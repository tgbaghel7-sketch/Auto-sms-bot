import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import ContextTypes, Application
from models import SessionLocal, get_or_create_user, get_user, User
from utils.firebase_manager import firebase_manager
from utils.filters_engine import should_forward, format_sms_message
from keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)

# Set from main.py after Application is built
_bot: Bot | None = None
_loop: asyncio.AbstractEventLoop | None = None


def set_runtime(bot: Bot, loop: asyncio.AbstractEventLoop):
    """Called once the Application has started so we have a live event loop."""
    global _bot, _loop
    _bot = bot
    _loop = loop


async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)

        if not user.firebase_type:
            await update.message.reply_text("❌ Connect Firebase first.")
            return
        if not user.channel_id:
            await update.message.reply_text("❌ Set a private channel first.")
            return
        if not user.selected_devices:
            await update.message.reply_text("❌ Select at least one device.")
            return

        success = firebase_manager.start_listening(user)
        if success:
            user.is_monitoring = True
            session.commit()
            await update.message.reply_text(
                "▶️ Monitoring started!\nNew SMS will be forwarded to your channel.",
                reply_markup=main_menu_keyboard(True),
            )
        else:
            await update.message.reply_text(
                "❌ Failed to start listeners. Check Firebase credentials / databaseURL."
            )
    finally:
        session.close()


async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        firebase_manager.stop_listening(user.telegram_id)
        user.is_monitoring = False
        session.commit()
        await update.message.reply_text(
            "⏹️ Monitoring stopped.",
            reply_markup=main_menu_keyboard(False),
        )
    finally:
        session.close()


def on_sms(telegram_id: int, device_id: str, data, path: str = None):
    """
    Synchronous callback invoked by firebase-admin listener threads.
    Schedules the actual Telegram send onto the bot's event loop.
    """
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
            if not user or not user.is_monitoring or not user.channel_id:
                return

            filters = user.filters or {}
            channel_id = user.channel_id

            messages = []
            for sms in sms_list:
                if not should_forward(sms, filters):
                    continue
                messages.append(format_sms_message(device_id, sms))
        finally:
            session.close()

        if not messages or _bot is None or _loop is None:
            if messages and (_bot is None or _loop is None):
                logger.warning("SMS arrived but bot/loop not ready yet")
            return

        for text in messages:
            future = asyncio.run_coroutine_threadsafe(
                _send_one(_bot, channel_id, text), _loop
            )
            try:
                future.result(timeout=20)
            except Exception as e:
                logger.error(f"Failed to send SMS to channel: {e}")

    except Exception as e:
        logger.error(f"on_sms error: {e}", exc_info=True)


async def _send_one(bot: Bot, channel_id: int, text: str):
    try:
        await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Telegram send_message failed: {e}")


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        firebase_manager.stop_listening(user.telegram_id)
        session.delete(user)
        session.commit()
        await update.message.reply_text(
            "🗑️ All your data has been deleted.\nYou can /start again anytime.",
            reply_markup=main_menu_keyboard(False),
        )
    finally:
        session.close()


def restore_active_listeners():
    """
    Called once at bot startup. Re-starts listeners for every user
    that had is_monitoring=True when the process last died.
    """
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.is_monitoring.is_(True)).all()
        logger.info(f"Restoring listeners for {len(users)} user(s)")
        for user in users:
            if (
                not user.firebase_type
                or not user.selected_devices
                or not user.channel_id
            ):
                user.is_monitoring = False
                continue
            ok = firebase_manager.start_listening(user)
            if not ok:
                user.is_monitoring = False
                logger.warning(f"Could not restore listener for {user.telegram_id}")
        session.commit()
    except Exception as e:
        logger.error(f"Failed to restore listeners: {e}", exc_info=True)
    finally:
        session.close()
