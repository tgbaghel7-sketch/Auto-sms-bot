import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from models import SessionLocal, get_or_create_user, Channel
from keyboards import channel_menu_keyboard, main_menu_keyboard, back_main_keyboard

logger = logging.getLogger(__name__)

WAITING_CHANNEL = 1


async def channel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 <b>Manage Channel</b>\n\n"
        "Add private channels where SMS will be forwarded.\n"
        "Bot must be admin with <b>Post Messages</b> permission.",
        parse_mode="HTML",
        reply_markup=channel_menu_keyboard(),
    )


async def channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "ch_add":
        await query.edit_message_text(
            "Forward any message from the private channel here,\n"
            "or send the channel ID (e.g. <code>-1001234567890</code>).",
            parse_mode="HTML",
            reply_markup=back_main_keyboard(),
        )
        return WAITING_CHANNEL

    if data == "ch_list":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            chs = session.query(Channel).filter(Channel.user_id == user.id).all()
            if not chs:
                text = "No channels added."
            else:
                lines = []
                for c in chs:
                    mark = "✅" if c.id == user.active_channel_id else "▫️"
                    lines.append(f"{mark} {c.name or c.channel_id} (<code>{c.channel_id}</code>)")
                text = "📋 <b>Channels:</b>\n\n" + "\n".join(lines)
        finally:
            session.close()
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=channel_menu_keyboard()
        )
        return ConversationHandler.END

    if data == "ch_select":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            chs = session.query(Channel).filter(Channel.user_id == user.id).all()
            if not chs:
                await query.edit_message_text(
                    "No channels. Add one first.", reply_markup=channel_menu_keyboard()
                )
                return ConversationHandler.END
            buttons = [
                [InlineKeyboardButton(
                    f"{'✅ ' if c.id == user.active_channel_id else ''}{c.name or c.channel_id}",
                    callback_data=f"ch_sel_{c.id}",
                )]
                for c in chs
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="ch_menu")])
        finally:
            session.close()
        await query.edit_message_text(
            "Select active channel:", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return ConversationHandler.END

    if data.startswith("ch_sel_"):
        cid = int(data.split("_")[-1])
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            ch = session.query(Channel).filter(
                Channel.id == cid, Channel.user_id == user.id
            ).first()
            if ch:
                user.active_channel_id = ch.id
                session.commit()
                await query.edit_message_text(
                    f"✅ Selected channel: <code>{ch.channel_id}</code>",
                    parse_mode="HTML",
                    reply_markup=channel_menu_keyboard(),
                )
            else:
                await query.edit_message_text("Not found.", reply_markup=channel_menu_keyboard())
        finally:
            session.close()
        return ConversationHandler.END

    if data == "ch_remove":
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            chs = session.query(Channel).filter(Channel.user_id == user.id).all()
            if not chs:
                await query.edit_message_text(
                    "Nothing to remove.", reply_markup=channel_menu_keyboard()
                )
                return ConversationHandler.END
            buttons = [
                [InlineKeyboardButton(
                    f"🗑 {c.name or c.channel_id}", callback_data=f"ch_del_{c.id}"
                )]
                for c in chs
            ]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="ch_menu")])
        finally:
            session.close()
        await query.edit_message_text(
            "Select channel to remove:", reply_markup=InlineKeyboardMarkup(buttons)
        )
        return ConversationHandler.END

    if data.startswith("ch_del_"):
        cid = int(data.split("_")[-1])
        session = SessionLocal()
        try:
            user = get_or_create_user(session, update.effective_user.id)
            ch = session.query(Channel).filter(
                Channel.id == cid, Channel.user_id == user.id
            ).first()
            if ch:
                if user.active_channel_id == ch.id:
                    user.active_channel_id = None
                session.delete(ch)
                session.commit()
                await query.edit_message_text(
                    "🗑 Channel removed.", reply_markup=channel_menu_keyboard()
                )
            else:
                await query.edit_message_text("Not found.", reply_markup=channel_menu_keyboard())
        finally:
            session.close()
        return ConversationHandler.END

    if data == "ch_menu":
        await query.edit_message_text(
            "📢 <b>Manage Channel</b>",
            parse_mode="HTML",
            reply_markup=channel_menu_keyboard(),
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = None
    name = None

    if update.message.forward_from_chat:
        chat_id = update.message.forward_from_chat.id
        name = update.message.forward_from_chat.title
    else:
        text = (update.message.text or "").strip()
        try:
            chat_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "Send a valid channel ID or forward a message from the channel."
            )
            return WAITING_CHANNEL

    # Test post permission
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Channel connected! You can delete this message.",
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Cannot post to this channel.\n"
            f"Make sure the bot is admin with Post Messages permission.\n\nError: {e}"
        )
        return WAITING_CHANNEL

    session = SessionLocal()
    try:
        user = get_or_create_user(session, update.effective_user.id)
        # avoid duplicates
        existing = (
            session.query(Channel)
            .filter(Channel.user_id == user.id, Channel.channel_id == chat_id)
            .first()
        )
        if existing:
            user.active_channel_id = existing.id
        else:
            ch = Channel(user_id=user.id, channel_id=chat_id, name=name)
            session.add(ch)
            session.flush()
            user.active_channel_id = ch.id
        session.commit()
        is_mon = user.is_monitoring
    finally:
        session.close()

    await update.message.reply_text(
        f"✅ Channel <code>{chat_id}</code> added and selected!",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_mon),
    )
    return ConversationHandler.END
