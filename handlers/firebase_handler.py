import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, FirebaseAccount
from keyboards import (
    firebase_menu_keyboard, firebase_type_keyboard,
    main_menu_keyboard, back_fb_keyboard, back_main_keyboard,
)

logger = logging.getLogger(__name__)

(
    WAIT_NAME,
    WAIT_URL_PUBLIC,
    WAIT_SA_JSON,
    WAIT_SA_URL,
    WAIT_SECRET_URL,
    WAIT_SECRET_KEY,
) = range(6)


async def firebase_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry from main menu button."""
    text = (
        "🔥 <b>Manage Firebase</b>\n\n"
        "Add multiple Firebase projects and select which one to monitor."
    )
    if update.message:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=firebase_menu_keyboard()
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=firebase_menu_keyboard()
        )


async def fb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "fb_menu":
        await query.edit_message_text(
            "🔥 <b>Manage Firebase</b>",
            parse_mode="HTML",
            reply_markup=firebase_menu_keyboard(),
        )
        return ConversationHandler.END

    if data == "fb_add":
        await query.edit_message_text(
            "Choose Firebase type:",
            reply_markup=firebase_type_keyboard(),
        )
        return ConversationHandler.END

    if data == "fbtype_public":
        context.user_data["fb_type"] = "public"
        await query.edit_message_text(
            "Send a <b>name</b> for this Firebase (e.g. My Public DB):",
            parse_mode="HTML",
            reply_markup=back_fb_keyboard(),
        )
        return WAIT_NAME

    if data == "fbtype_sa":
        context.user_data["fb_type"] = "private_sa"
        await query.edit_message_text(
            "Send a <b>name</b> for this Firebase (e.g. Work Project):",
            parse_mode="HTML",
            reply_markup=back_fb_keyboard(),
        )
        return WAIT_NAME

    if data == "fbtype_secret":
        context.user_data["fb_type"] = "private_secret"
        await query.edit_message_text(
            "Send a <b>name</b> for this Firebase:",
            parse_mode="HTML",
            reply_markup=back_fb_keyboard(),
        )
        return WAIT_NAME

    if data == "fb_list":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            fbs = session.query(FirebaseAccount).filter(
                FirebaseAccount.user_id == user.id
            ).all()
            if not fbs:
                text = "No Firebase accounts added yet."
            else:
                lines = []
                for f in fbs:
                    mark = "✅" if f.id == user.active_firebase_id else "▫️"
                    lines.append(f"{mark} <b>{f.name}</b> ({f.fb_type})\n<code>{f.database_url}</code>")
                text = "📋 <b>Your Firebases:</b>\n\n" + "\n\n".join(lines)
        finally:
            session.close()
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=firebase_menu_keyboard()
        )
        return ConversationHandler.END

    if data == "fb_select":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            fbs = session.query(FirebaseAccount).filter(
                FirebaseAccount.user_id == user.id
            ).all()
            if not fbs:
                await query.edit_message_text(
                    "No Firebase accounts. Add one first.",
                    reply_markup=firebase_menu_keyboard(),
                )
                return ConversationHandler.END
            buttons = [
                [InlineKeyboardButton(
                    f"{'✅ ' if f.id == user.active_firebase_id else ''}{f.name}",
                    callback_data=f"fb_sel_{f.id}",
                )]
                for f in fbs
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_menu")])
        finally:
            session.close()
        await query.edit_message_text(
            "Select which Firebase to monitor:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return ConversationHandler.END

    if data.startswith("fb_sel_"):
        fb_id = int(data.split("_")[-1])
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            fb = session.query(FirebaseAccount).filter(
                FirebaseAccount.id == fb_id,
                FirebaseAccount.user_id == user.id,
            ).first()
            if fb:
                user.active_firebase_id = fb.id
                # clear devices when switching Firebase
                user.selected_devices = []
                session.commit()
                await query.edit_message_text(
                    f"✅ Selected Firebase: <b>{fb.name}</b>\n\n"
                    "Devices were cleared – please add devices for this Firebase.",
                    parse_mode="HTML",
                    reply_markup=firebase_menu_keyboard(),
                )
            else:
                await query.edit_message_text("Not found.", reply_markup=firebase_menu_keyboard())
        finally:
            session.close()
        return ConversationHandler.END

    if data == "fb_delete":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            fbs = session.query(FirebaseAccount).filter(
                FirebaseAccount.user_id == user.id
            ).all()
            if not fbs:
                await query.edit_message_text(
                    "Nothing to delete.", reply_markup=firebase_menu_keyboard()
                )
                return ConversationHandler.END
            buttons = [
                [InlineKeyboardButton(f"🗑 {f.name}", callback_data=f"fb_del_{f.id}")]
                for f in fbs
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_menu")])
        finally:
            session.close()
        await query.edit_message_text(
            "Select Firebase to delete:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return ConversationHandler.END

    if data.startswith("fb_del_"):
        fb_id = int(data.split("_")[-1])
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            fb = session.query(FirebaseAccount).filter(
                FirebaseAccount.id == fb_id,
                FirebaseAccount.user_id == user.id,
            ).first()
            if fb:
                name = fb.name
                if user.active_firebase_id == fb.id:
                    user.active_firebase_id = None
                    user.selected_devices = []
                    user.is_monitoring = False
                session.delete(fb)
                session.commit()
                await query.edit_message_text(
                    f"🗑 Deleted <b>{name}</b>",
                    parse_mode="HTML",
                    reply_markup=firebase_menu_keyboard(),
                )
            else:
                await query.edit_message_text("Not found.", reply_markup=firebase_menu_keyboard())
        finally:
            session.close()
        return ConversationHandler.END

    return ConversationHandler.END


# ── conversation steps for adding ───────────────────────────
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fb_name"] = update.message.text.strip()[:100]
    fb_type = context.user_data.get("fb_type")

    if fb_type == "public":
        await update.message.reply_text(
            "Send the <b>Realtime Database URL</b>\n"
            "Example: <code>https://myproject-default-rtdb.firebaseio.com</code>",
            parse_mode="HTML",
        )
        return WAIT_URL_PUBLIC

    if fb_type == "private_sa":
        await update.message.reply_text(
            "Upload the <b>Service Account JSON</b> file now.",
            parse_mode="HTML",
        )
        return WAIT_SA_JSON

    if fb_type == "private_secret":
        await update.message.reply_text(
            "Send the <b>Realtime Database URL</b>\n"
            "Example: <code>https://myproject-default-rtdb.firebaseio.com</code>",
            parse_mode="HTML",
        )
        return WAIT_SECRET_URL

    await update.message.reply_text("Something went wrong. Start again.")
    return ConversationHandler.END


async def receive_public_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip().rstrip("/")
    if not url.startswith("https://") or "firebaseio.com" not in url:
        await update.message.reply_text("Invalid URL. Must contain firebaseio.com")
        return WAIT_URL_PUBLIC

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        fb = FirebaseAccount(
            user_id=user.id,
            name=context.user_data.get("fb_name", "Public"),
            fb_type="public",
            database_url=url,
            credentials=None,
        )
        session.add(fb)
        session.flush()
        user.active_firebase_id = fb.id
        session.commit()
    finally:
        session.close()

    await update.message.reply_text(
        f"✅ Public Firebase <b>{context.user_data.get('fb_name')}</b> added and selected!",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(False),
    )
    return ConversationHandler.END


async def receive_sa_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Please send a .json file.")
        return WAIT_SA_JSON
    doc = update.message.document
    if not (doc.file_name or "").lower().endswith(".json"):
        await update.message.reply_text("File must be .json")
        return WAIT_SA_JSON

    file = await doc.get_file()
    content = await file.download_as_bytearray()
    try:
        sa_dict = json.loads(content.decode())
        if "private_key" not in sa_dict or "project_id" not in sa_dict:
            raise ValueError("Not a valid Service Account JSON")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid JSON: {e}")
        return WAIT_SA_JSON

    context.user_data["sa_dict"] = sa_dict
    url = sa_dict.get("databaseURL") or sa_dict.get("database_url")
    if url:
        context.user_data["sa_url"] = url
        return await _save_sa(update, context)

    await update.message.reply_text(
        "JSON looks good. Now send the <b>Realtime Database URL</b>:\n"
        "<code>https://xxx-default-rtdb.firebaseio.com</code>",
        parse_mode="HTML",
    )
    return WAIT_SA_URL


async def receive_sa_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip().rstrip("/")
    if not url.startswith("https://") or "firebaseio.com" not in url:
        await update.message.reply_text("Invalid URL.")
        return WAIT_SA_URL
    context.user_data["sa_url"] = url
    return await _save_sa(update, context)


async def _save_sa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sa_dict = context.user_data.get("sa_dict")
    url = context.user_data.get("sa_url")
    if not sa_dict or not url:
        await update.message.reply_text("Error – start again.")
        return ConversationHandler.END

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        fb = FirebaseAccount(
            user_id=user.id,
            name=context.user_data.get("fb_name", "Private SA"),
            fb_type="private_sa",
            database_url=url,
            credentials=json.dumps(sa_dict),
        )
        session.add(fb)
        session.flush()
        user.active_firebase_id = fb.id
        session.commit()
    finally:
        session.close()

    for k in ("sa_dict", "sa_url", "fb_name", "fb_type"):
        context.user_data.pop(k, None)

    await update.message.reply_text(
        "✅ Private Firebase (Service Account) added and selected!",
        reply_markup=main_menu_keyboard(False),
    )
    return ConversationHandler.END


async def receive_secret_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip().rstrip("/")
    if not url.startswith("https://") or "firebaseio.com" not in url:
        await update.message.reply_text("Invalid URL.")
        return WAIT_SECRET_URL
    context.user_data["secret_url"] = url
    await update.message.reply_text(
        "Now send the <b>Database Secret</b>\n"
        "(Firebase Console → Project Settings → Service accounts → Database secrets)",
        parse_mode="HTML",
    )
    return WAIT_SECRET_KEY


async def receive_secret_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text.strip()
    url = context.user_data.get("secret_url")
    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        fb = FirebaseAccount(
            user_id=user.id,
            name=context.user_data.get("fb_name", "Private Secret"),
            fb_type="private_secret",
            database_url=url,
            credentials=secret,
        )
        session.add(fb)
        session.flush()
        user.active_firebase_id = fb.id
        session.commit()
    finally:
        session.close()

    await update.message.reply_text(
        "✅ Private Firebase (URL + Secret) added and selected!",
        reply_markup=main_menu_keyboard(False),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelled.", reply_markup=main_menu_keyboard(False)
    )
    return ConversationHandler.END
