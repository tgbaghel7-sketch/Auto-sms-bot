import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, mark_json_dirty
from keyboards import filters_menu_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

WAITING_KW, WAITING_RE, WAITING_WL, WAITING_BL = range(4)


async def filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 <b>Filters</b>\n\n"
        "Only SMS that pass filters are forwarded.\n"
        "Empty filters = forward everything.",
        parse_mode="HTML",
        reply_markup=filters_menu_keyboard(),
    )


async def filters_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "flt_kw":
        await query.edit_message_text(
            "Send a keyword (case-insensitive):", reply_markup=back_main_keyboard()
        )
        return WAITING_KW
    if data == "flt_re":
        await query.edit_message_text(
            "Send a regex (e.g. <code>\\d{6}</code>):",
            parse_mode="HTML",
            reply_markup=back_main_keyboard(),
        )
        return WAITING_RE
    if data == "flt_wl":
        await query.edit_message_text(
            "Send a sender to whitelist:", reply_markup=back_main_keyboard()
        )
        return WAITING_WL
    if data == "flt_bl":
        await query.edit_message_text(
            "Send a sender to blacklist:", reply_markup=back_main_keyboard()
        )
        return WAITING_BL

    if data == "flt_view":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            f = user.filters or {}
            text = (
                f"<b>Current Filters</b>\n\n"
                f"Keywords: {f.get('keywords', [])}\n"
                f"Regex: {f.get('regex', [])}\n"
                f"Whitelist: {f.get('whitelist', [])}\n"
                f"Blacklist: {f.get('blacklist', [])}"
            )
        finally:
            session.close()
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=back_main_keyboard()
        )
        return ConversationHandler.END

    if data == "flt_clear":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            user.filters = {
                "keywords": [], "regex": [], "whitelist": [], "blacklist": []
            }
            mark_json_dirty(user, "filters")
            session.commit()
        finally:
            session.close()
        await query.edit_message_text(
            "🧹 All filters cleared.", reply_markup=back_main_keyboard()
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def _add(update: Update, key: str):
    value = update.message.text.strip()
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        filters = dict(
            user.filters
            or {"keywords": [], "regex": [], "whitelist": [], "blacklist": []}
        )
        lst = list(filters.get(key, []))
        if value not in lst:
            lst.append(value)
            filters[key] = lst
            user.filters = filters
            mark_json_dirty(user, "filters")
            session.commit()
        await update.message.reply_text(
            f"✅ Added to {key}: <code>{value}</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user.is_monitoring),
        )
    finally:
        session.close()
    return ConversationHandler.END


async def receive_kw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _add(update, "keywords")


async def receive_re(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _add(update, "regex")


async def receive_wl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _add(update, "whitelist")


async def receive_bl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _add(update, "blacklist")
