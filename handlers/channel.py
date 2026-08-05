import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user
from keyboards import main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

WAITING_CHANNEL = 1


async def set_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 <b>Set Private Channel</b>\n\n"
        "1. Create a private channel\n"
        "2. Add this bot as <b>administrator</b> (with post messages permission)\n"
        "3. Forward any message from that channel to me, <b>or</b> send the channel ID (e.g. -1001234567890)\n\n"
        "You can also just type the channel ID.",
        parse_mode="HTML"
    )
    return WAITING_CHANNEL


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = None

    # If user forwarded a message from the channel
    if update.message.forward_from_chat:
        chat_id = update.message.forward_from_chat.id
    else:
        text = update.message.text.strip()
        try:
            chat_id = int(text)
        except ValueError:
            await update.message.reply_text("Please send a valid channel ID or forward a message from the channel.")
            return WAITING_CHANNEL

    # Test if bot can post
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Channel connected successfully! This message can be deleted."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Cannot post to this channel.\n"
            f"Make sure the bot is admin with 'Post Messages' permission.\n\nError: {e}"
        )
        return WAITING_CHANNEL

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        user.channel_id = chat_id
        session.commit()
        is_mon = user.is_monitoring
    finally:
        session.close()

    await update.message.reply_text(
        f"✅ Channel set to <code>{chat_id}</code>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_mon)
    )
    return ConversationHandler.END
