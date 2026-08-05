import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, FirebaseAccount, mark_json_dirty
from utils.firebase_manager import firebase_manager
from keyboards import devices_menu_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)


async def devices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show device menu. Prefer auto-fetch from Firebase."""
    await update.message.reply_text(
        "📱 <b>Device</b>\n\n"
        "Tap <b>Select Devices</b> to load all devices from your active Firebase "
        "and choose which ones to monitor.",
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

        # ── Select / refresh device list from Firebase ──
        if data in ("dev_select", "dev_list", "dev_refresh"):
            if not user.active_firebase_id:
                await query.edit_message_text(
                    "❌ Select a Firebase first (Manage Firebase → Select).",
                    reply_markup=back_main_keyboard(),
                )
                return ConversationHandler.END

            fb = (
                session.query(FirebaseAccount)
                .filter(FirebaseAccount.id == user.active_firebase_id)
                .first()
            )
            if not fb:
                await query.edit_message_text(
                    "❌ Active Firebase not found.",
                    reply_markup=back_main_keyboard(),
                )
                return ConversationHandler.END

            await query.edit_message_text("⏳ Loading devices from Firebase…")

            devices = firebase_manager.list_devices(fb)
            selected = set(user.selected_devices or [])

            if not devices:
                await query.edit_message_text(
                    "No devices found under <code>/devices</code>.\n\n"
                    "Make sure your Firebase has data at:\n"
                    "<code>/devices/{deviceId}/sms/...</code>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Refresh", callback_data="dev_refresh")],
                        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
                    ]),
                )
                return ConversationHandler.END

            # Build toggle buttons
            buttons = []
            for d in devices:
                mark = "✅" if d in selected else "⬜"
                buttons.append([
                    InlineKeyboardButton(
                        f"{mark} {d}",
                        callback_data=f"dev_toggle_{d}",
                    )
                ])
            buttons.append([
                InlineKeyboardButton("🔄 Refresh", callback_data="dev_refresh"),
                InlineKeyboardButton("✅ Done", callback_data="dev_done"),
            ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])

            selected_count = len(selected)
            await query.edit_message_text(
                f"📱 <b>Select devices to monitor</b>\n\n"
                f"Firebase: <b>{fb.name}</b>\n"
                f"Selected: {selected_count}\n\n"
                f"Tap a device to select / deselect:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return ConversationHandler.END

        # ── Toggle one device ──
        if data.startswith("dev_toggle_"):
            device_id = data[len("dev_toggle_"):]
            devices = list(user.selected_devices or [])
            if device_id in devices:
                devices.remove(device_id)
            else:
                devices.append(device_id)
            user.selected_devices = devices
            mark_json_dirty(user, "selected_devices")
            session.commit()

            # Re-render the list
            fb = (
                session.query(FirebaseAccount)
                .filter(FirebaseAccount.id == user.active_firebase_id)
                .first()
            )
            all_devices = firebase_manager.list_devices(fb) if fb else devices
            selected = set(devices)

            buttons = []
            for d in all_devices:
                mark = "✅" if d in selected else "⬜"
                buttons.append([
                    InlineKeyboardButton(
                        f"{mark} {d}",
                        callback_data=f"dev_toggle_{d}",
                    )
                ])
            buttons.append([
                InlineKeyboardButton("🔄 Refresh", callback_data="dev_refresh"),
                InlineKeyboardButton("✅ Done", callback_data="dev_done"),
            ])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])

            await query.edit_message_text(
                f"📱 <b>Select devices to monitor</b>\n\n"
                f"Firebase: <b>{fb.name if fb else '?'}</b>\n"
                f"Selected: {len(selected)}\n\n"
                f"Tap a device to select / deselect:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return ConversationHandler.END

        # ── Done ──
        if data == "dev_done":
            selected = user.selected_devices or []
            text = (
                f"✅ Devices updated.\n"
                f"Monitoring: <code>{', '.join(selected) if selected else 'None'}</code>"
            )
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=back_main_keyboard(),
            )
            return ConversationHandler.END

        # ── Clear all selected ──
        if data == "dev_clear":
            user.selected_devices = []
            mark_json_dirty(user, "selected_devices")
            session.commit()
            await query.edit_message_text(
                "🗑 All selected devices cleared.",
                reply_markup=devices_menu_keyboard(),
            )
            return ConversationHandler.END

    finally:
        session.close()

    return ConversationHandler.END
