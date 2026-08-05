import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, FirebaseAccount, mark_json_dirty
from utils.firebase_manager import firebase_manager
from keyboards import devices_menu_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

WAITING_ADD, WAITING_REMOVE = range(2)


async def devices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 <b>Device</b>\n\n"
        "Devices are read from the <b>active</b> Firebase:\n"
        "<code>/devices/{deviceId}/sms/...</code>",
        parse_mode="HTML",
        reply_markup=devices_menu_keyboard(),
    )


async def devices_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)

        if data == "dev_list":
            if not user.active_firebase_id:
                await query.edit_message_text(
                    "❌ Select a Firebase first.", reply_markup=back_main_keyboard()
                )
                return
            fb = session.query(FirebaseAccount).filter(
                FirebaseAccount.id == user.active_firebase_id
            ).first()
            if not fb:
                await query.edit_message_text(
                    "❌ Active Firebase not found.", reply_markup=back_main_keyboard()
                )
                return
            devices = firebase_manager.list_devices(fb)
            selected = set(user.selected_devices or [])
            if not devices:
                text = "No devices found under <code>/devices</code>."
            else:
                lines = [
                    f"{'✅' if d in selected else '⬜'} <code>{d}</code>"
                    for d in devices
                ]
                text = "📋 <b>Devices:</b>\n\n" + "\n".join(lines)
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=back_main_keyboard()
            )
            return

        if data == "dev_add":
            await query.edit_message_text(
                "Send the <b>device ID</b> to add:",
                parse_mode="HTML",
                reply_markup=back_main_keyboard(),
            )
            return WAITING_ADD

        if data == "dev_remove":
            await query.edit_message_text(
                "Send the <b>device ID</b> to remove:",
                parse_mode="HTML",
                reply_markup=back_main_keyboard(),
            )
            return WAITING_REMOVE
    finally:
        session.close()
    return ConversationHandler.END


async def receive_add_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        devices = list(user.selected_devices or [])
        if device_id not in devices:
            devices.append(device_id)
            user.selected_devices = devices
            mark_json_dirty(user, "selected_devices")
            session.commit()
        await update.message.reply_text(
            f"✅ Device <code>{device_id}</code> added.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.is_monitoring),
        )
    finally:
        session.close()
    return ConversationHandler.END


async def receive_remove_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        devices = list(user.selected_devices or [])
        if device_id in devices:
            devices.remove(device_id)
            user.selected_devices = devices
            mark_json_dirty(user, "selected_devices")
            session.commit()
        await update.message.reply_text(
            f"🗑 Device <code>{device_id}</code> removed.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.is_monitoring),
        )
    finally:
        session.close()
    return ConversationHandler.END
