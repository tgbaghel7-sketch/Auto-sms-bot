import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, mark_json_dirty
from utils.firebase_manager import firebase_manager
from keyboards import devices_menu_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

WAITING_SELECT, WAITING_DESELECT = range(2)


async def manage_devices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 <b>Manage Devices</b>\n\n"
        "Devices are read from your Firebase path:\n"
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
            if not user.firebase_type:
                await query.edit_message_text(
                    "❌ Connect Firebase first.", reply_markup=back_main_keyboard()
                )
                return

            devices = firebase_manager.get_devices(user)
            if not devices:
                text = "No devices found under <code>/devices</code>."
            else:
                selected = set(user.selected_devices or [])
                lines = []
                for d in devices:
                    mark = "✅" if d in selected else "⬜"
                    lines.append(f"{mark} <code>{d}</code>")
                text = "📋 <b>Devices in your Firebase:</b>\n\n" + "\n".join(lines)

            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=back_main_keyboard()
            )
            return

        if data == "dev_select":
            await query.edit_message_text(
                "Send the <b>device ID</b> you want to monitor:",
                parse_mode="HTML",
                reply_markup=back_main_keyboard(),
            )
            return WAITING_SELECT

        if data == "dev_deselect":
            await query.edit_message_text(
                "Send the <b>device ID</b> you want to remove:",
                parse_mode="HTML",
                reply_markup=back_main_keyboard(),
            )
            return WAITING_DESELECT

    finally:
        session.close()

    return ConversationHandler.END


async def receive_select_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def receive_deselect_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            f"❌ Device <code>{device_id}</code> removed.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.is_monitoring),
        )
    finally:
        session.close()
    return ConversationHandler.END
