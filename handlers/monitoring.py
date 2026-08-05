import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import ContextTypes
from models import SessionLocal, get_or_create_user, get_user, User, Channel, FirebaseAccount
from utils.firebase_manager import firebase_manager
from utils.filters_engine import should_forward, format_sms_message
from keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_loop: asyncio.AbstractEventLoop | None = None


def set_runtime(bot: Bot, loop: asyncio.AbstractEventLoop):
    global _bot, _loop
    _bot = bot
    _loop = loop


async def start_forwarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)

        if not user.active_firebase_id:
            await update.message.reply_text("❌ Select a Firebase first (Manage Firebase → Select).")
            return
        if not user.active_channel_id:
            await update.message.reply_text("❌ Select a Channel first (Manage Channel → Select).")
            return
        if not user.selected_devices:
            await update.message.reply_text("❌ Add at least one Device.")
            return

        ok = firebase_manager.start_listening(user, session)
        if ok:
            user.is_monitoring = True
            session.commit()
            await update.message.reply_text(
                "▶️ Forwarding started!\nNew SMS will be sent to your channel.",
                reply_markup=main_menu_keyboard(True),
            )
        else:
            await update.message.reply_text(
                "❌ Failed to start. Check Firebase credentials / URL."
            )
    finally:
        session.close()


async def stop_forwarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        firebase_manager.stop_listening(user.telegram_id)
        user.is_monitoring = False
        session.commit()
        await update.message.reply_text(
            "⏹ Forwarding stopped.",
            reply_markup=main_menu_keyboard(False),
        )
    finally:
        session.close()


def on_sms(telegram_id: int, device_id: str, data, path=None, fb_name: str = ""):
    """Called from Firebase listener / poller threads."""
    try:
        if isinstance(data, dict) and (
            "from" in data or "body" in data or "text" in data or "message" in data
        ):
            sms_list = [data]
        elif isinstance(data, dict):
            sms_list = [v for v in data.values() if isinstance(v, dict)]
        else:
            return
        if not sms_list:
            return

        session = SessionLocal()
        try:
            user = get_user(session, telegram_id)
            if not user or not user.is_monitoring or not user.active_channel_id:
                return
            ch = session.query(Channel).filter(Channel.id == user.active_channel_id).first()
            if not ch:
                return
            channel_id = ch.channel_id
            filters = user.filters or {}
            messages = []
            for sms in sms_list:
                if should_forward(sms, filters):
                    messages.append(format_sms_message(device_id, sms, fb_name))
        finally:
            session.close()

        if not messages or _bot is None or _loop is None:
            return

        for text in messages:
            fut = asyncio.run_coroutine_threadsafe(
                _send(_bot, channel_id, text), _loop
            )
            try:
                fut.result(timeout=20)
            except Exception as e:
                logger.error(f"Send failed: {e}")
    except Exception as e:
        logger.error(f"on_sms error: {e}", exc_info=True)


async def _send(bot: Bot, channel_id: int, text: str):
    try:
        await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")


def restore_active_listeners():
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.is_monitoring.is_(True)).all()
        logger.info(f"Restoring listeners for {len(users)} user(s)")
        for user in users:
            if not user.active_firebase_id or not user.active_channel_id or not user.selected_devices:
                user.is_monitoring = False
                continue
            ok = firebase_manager.start_listening(user, session)
            if not ok:
                user.is_monitoring = False
                logger.warning(f"Could not restore {user.telegram_id}")
        session.commit()
    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
    finally:
        session.close()
