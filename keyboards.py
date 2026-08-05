from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard(is_monitoring: bool = False) -> ReplyKeyboardMarkup:
    btn = "⏹ Stop Forwarding" if is_monitoring else "▶️ Start Forwarding"
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔥 Manage Firebase"), KeyboardButton("📱 Device")],
            [KeyboardButton("📢 Manage Channel"), KeyboardButton("🔍 Filters")],
            [KeyboardButton(btn), KeyboardButton("📊 Status")],
        ],
        resize_keyboard=True,
    )


def firebase_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Firebase", callback_data="fb_add")],
        [InlineKeyboardButton("🗑 Delete Firebase", callback_data="fb_delete")],
        [InlineKeyboardButton("✅ Select Firebase", callback_data="fb_select")],
        [InlineKeyboardButton("📋 List Firebases", callback_data="fb_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def firebase_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Public (URL only)", callback_data="fbtype_public")],
        [InlineKeyboardButton("🔒 Private – Service Account JSON", callback_data="fbtype_sa")],
        [InlineKeyboardButton("🔑 Private – URL + Secret", callback_data="fbtype_secret")],
        [InlineKeyboardButton("🔙 Back", callback_data="fb_menu")],
    ])


def devices_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Device", callback_data="dev_add")],
        [InlineKeyboardButton("🗑 Remove Device", callback_data="dev_remove")],
        [InlineKeyboardButton("📋 List Devices", callback_data="dev_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def channel_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="ch_add")],
        [InlineKeyboardButton("🗑 Remove Channel", callback_data="ch_remove")],
        [InlineKeyboardButton("✅ Select Channel", callback_data="ch_select")],
        [InlineKeyboardButton("📋 List Channels", callback_data="ch_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def filters_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Set Keyword", callback_data="flt_kw")],
        [InlineKeyboardButton("➕ Set Regex", callback_data="flt_re")],
        [InlineKeyboardButton("➕ Whitelist Sender", callback_data="flt_wl")],
        [InlineKeyboardButton("➕ Blacklist Sender", callback_data="flt_bl")],
        [InlineKeyboardButton("👀 View Filters", callback_data="flt_view")],
        [InlineKeyboardButton("🧹 Clear All Filters", callback_data="flt_clear")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def back_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
    ])


def back_fb_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="fb_menu")]
    ])
