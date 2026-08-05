from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def main_menu_keyboard(is_monitoring: bool = False) -> ReplyKeyboardMarkup:
    monitor_btn = "⏹️ Stop Monitoring" if is_monitoring else "▶️ Start Monitoring"
    keyboard = [
        [KeyboardButton("🔗 Connect Firebase"), KeyboardButton("📢 Set Channel")],
        [KeyboardButton("📱 Manage Devices"), KeyboardButton("🔍 Filters")],
        [KeyboardButton(monitor_btn), KeyboardButton("📊 Status")],
        [KeyboardButton("🗑️ Logout / Delete Data")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def firebase_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Upload Service Account JSON", callback_data="fb_sa")],
        [InlineKeyboardButton("🔑 Database URL + Secret", callback_data="fb_secret")],
        [InlineKeyboardButton("◀️ Back to Main", callback_data="back_main")],
    ])


def devices_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 List Devices", callback_data="dev_list")],
        [InlineKeyboardButton("✅ Select Device", callback_data="dev_select")],
        [InlineKeyboardButton("❌ Deselect Device", callback_data="dev_deselect")],
        [InlineKeyboardButton("◀️ Back to Main", callback_data="back_main")],
    ])


def filters_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Keyword", callback_data="flt_add_kw")],
        [InlineKeyboardButton("➕ Add Regex", callback_data="flt_add_re")],
        [InlineKeyboardButton("➕ Whitelist Sender", callback_data="flt_add_wl")],
        [InlineKeyboardButton("➕ Blacklist Sender", callback_data="flt_add_bl")],
        [InlineKeyboardButton("👀 View Filters", callback_data="flt_view")],
        [InlineKeyboardButton("🧹 Clear All Filters", callback_data="flt_clear")],
        [InlineKeyboardButton("◀️ Back to Main", callback_data="back_main")],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ No", callback_data="back_main"),
        ]
    ])


def back_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Main Menu", callback_data="back_main")]
    ])
