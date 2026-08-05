import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import SessionLocal, get_or_create_user
from keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = SessionLocal()
    try:
        db_user = get_or_create_user(
            session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        is_mon = db_user.is_monitoring
    finally:
        session.close()

    text = (
        f"👋 Welcome <b>{user.first_name or 'User'}</b>!\n\n"
        "This bot monitors <b>your own</b> Firebase Realtime Database "
        "and forwards new SMS to your private Telegram channel.\n\n"
        "🔒 Your credentials and data are completely private.\n\n"
        "Use the buttons below to get started."
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_mon)
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    session = SessionLocal()
    try:
        db_user = get_or_create_user(session, update.effective_user.id)
        is_mon = db_user.is_monitoring
    finally:
        session.close()

    await query.edit_message_text(
        "🏠 Main Menu",
        reply_markup=None
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Choose an option:",
        reply_markup=main_menu_keyboard(is_mon)
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        fb_status = "✅ Connected" if user.firebase_type else "❌ Not connected"
        ch_status = f"✅ `{user.channel_id}`" if user.channel_id else "❌ Not set"
        devices = ", ".join(user.selected_devices) if user.selected_devices else "None"
        mon = "🟢 Active" if user.is_monitoring else "🔴 Stopped"

        filters = user.filters or {}
        flt_summary = (
            f"Keywords: {len(filters.get('keywords', []))}\n"
            f"Regex: {len(filters.get('regex', []))}\n"
            f"Whitelist: {len(filters.get('whitelist', []))}\n"
            f"Blacklist: {len(filters.get('blacklist', []))}"
        )

        text = (
            f"📊 <b>Your Status</b>\n\n"
            f"Firebase: {fb_status} ({user.firebase_type or '-'})\n"
            f"Channel: {ch_status}\n"
            f"Selected Devices: <code>{devices}</code>\n"
            f"Monitoring: {mon}\n\n"
            f"<b>Filters:</b>\n{flt_summary}"
        )
    finally:
        session.close()

    await update.message.reply_text(text, parse_mode="HTML")
