import json
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user
from utils.encryption import encrypt
from keyboards import firebase_method_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

# Conversation states
WAITING_SA_JSON, WAITING_SA_URL, WAITING_URL, WAITING_SECRET = range(4)


async def connect_firebase_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 <b>Connect your Firebase Realtime Database</b>\n\n"
        "• <b>Service Account JSON</b> (recommended – full real-time support)\n"
        "• <b>Database URL + Secret</b> (legacy – not supported for listeners)",
        parse_mode="HTML",
        reply_markup=firebase_method_keyboard(),
    )


async def fb_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "fb_sa":
        await query.edit_message_text(
            "📄 Please <b>upload the Service Account JSON file</b> now.\n\n"
            "How to get it:\n"
            "1. Firebase Console → Project Settings → Service accounts\n"
            "2. Generate new private key\n"
            "3. Download the JSON and send it here as a document.",
            parse_mode="HTML",
            reply_markup=back_main_keyboard(),
        )
        return WAITING_SA_JSON

    if data == "fb_secret":
        await query.edit_message_text(
            "⚠️ <b>Database Secret is no longer supported</b> by the official "
            "firebase-admin SDK for real-time listeners.\n\n"
            "Please use <b>Service Account JSON</b> instead.",
            parse_mode="HTML",
            reply_markup=back_main_keyboard(),
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_sa_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("Please send a JSON document.")
        return WAITING_SA_JSON

    doc = update.message.document
    if not (doc.file_name or "").lower().endswith(".json"):
        await update.message.reply_text("File must be a .json")
        return WAITING_SA_JSON

    file = await doc.get_file()
    content = await file.download_as_bytearray()
    try:
        sa_dict = json.loads(content.decode())
        if "private_key" not in sa_dict or "project_id" not in sa_dict:
            raise ValueError("Missing private_key or project_id – not a valid service account")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid JSON: {e}")
        return WAITING_SA_JSON

    # Store temporarily; we still need the Realtime Database URL
    context.user_data["sa_dict"] = sa_dict

    # Many SA JSONs do NOT contain databaseURL – always ask
    url = sa_dict.get("databaseURL") or sa_dict.get("database_url")
    if url:
        context.user_data["fb_url"] = url
        return await _save_sa(update, context)

    await update.message.reply_text(
        "📄 Service Account looks good.\n\n"
        "Now send your <b>Realtime Database URL</b>.\n"
        "Example: <code>https://myproject-default-rtdb.firebaseio.com</code>\n\n"
        "(Firebase Console → Realtime Database → Data tab → copy the URL at the top)",
        parse_mode="HTML",
    )
    return WAITING_SA_URL


async def receive_sa_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip().rstrip("/")
    if not url.startswith("https://") or "firebaseio.com" not in url:
        await update.message.reply_text(
            "Please send a valid Firebase Realtime Database URL "
            "(must contain firebaseio.com)."
        )
        return WAITING_SA_URL

    context.user_data["fb_url"] = url
    return await _save_sa(update, context)


async def _save_sa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sa_dict = context.user_data.get("sa_dict")
    url = context.user_data.get("fb_url")
    if not sa_dict or not url:
        await update.message.reply_text("Something went wrong. Please start again.")
        return ConversationHandler.END

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        user.firebase_type = "service_account"
        user.firebase_service_account = encrypt(json.dumps(sa_dict))
        user.firebase_url = encrypt(url)
        user.firebase_secret = None
        session.commit()
    finally:
        session.close()

    # Clean temp data
    context.user_data.pop("sa_dict", None)
    context.user_data.pop("fb_url", None)

    await update.message.reply_text(
        "✅ Service Account + Database URL saved securely!\n\n"
        "Next steps:\n"
        "1. Set your private channel\n"
        "2. Select devices\n"
        "3. Start Monitoring",
        reply_markup=main_menu_keyboard(False),
    )
    return ConversationHandler.END


# Legacy handlers kept so ConversationHandler states stay consistent
async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Database Secret method is no longer supported. Use Service Account JSON."
    )
    return ConversationHandler.END


async def receive_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Database Secret method is no longer supported. Use Service Account JSON."
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelled.", reply_markup=main_menu_keyboard(False)
    )
    return ConversationHandler.END
