import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import SessionLocal, get_or_create_user, FirebaseAccount, Channel
from keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = SessionLocal()
    try:
        db_user = get_or_create_user(
            session, user.id, username=user.username, first_name=user.first_name
        )
        is_mon = db_user.is_monitoring
    finally:
        session.close()

    await update.message.reply_text(
        f"👋 Welcome <b>{user.first_name or 'User'}</b>!\n\n"
        "This bot monitors Firebase Realtime Database and forwards SMS "
        "to your Telegram channel.\n\n"
        "You can add <b>multiple</b> Firebase projects (public or private) "
        "and switch between them.\n\n"
        "Use the buttons below to get started.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_mon),
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

    session = SessionLocal()
    try:
        db_user = get_or_create_user(session, update.effective_user.id)
        is_mon = db_user.is_monitoring
    finally:
        session.close()

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="🏠 <b>Main Menu</b>\nChoose an option:",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_mon),
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)

        fb_name = "❌ None selected"
        if user.active_firebase_id:
            fb = session.query(FirebaseAccount).filter(
                FirebaseAccount.id == user.active_firebase_id
            ).first()
            if fb:
                fb_name = f"✅ {fb.name} ({fb.fb_type})"

        ch_name = "❌ None selected"
        if user.active_channel_id:
            ch = session.query(Channel).filter(
                Channel.id == user.active_channel_id
            ).first()
            if ch:
                ch_name = f"✅ {ch.name or ch.channel_id}"

        devices = ", ".join(user.selected_devices or []) or "None"
        mon = "🟢 Active" if user.is_monitoring else "🔴 Stopped"
        f = user.filters or {}

        text = (
            f"📊 <b>Status</b>\n\n"
            f"🔥 Firebase: {fb_name}\n"
            f"📢 Channel: {ch_name}\n"
            f"📱 Devices: <code>{devices}</code>\n"
            f"Forwarding: {mon}\n\n"
            f"<b>Filters</b>\n"
            f"Keywords: {len(f.get('keywords', []))}\n"
            f"Regex: {len(f.get('regex', []))}\n"
            f"Whitelist: {len(f.get('whitelist', []))}\n"
            f"Blacklist: {len(f.get('blacklist', []))}"
        )
    finally:
        session.close()

    await update.message.reply_text(text, parse_mode="HTML")
