import logging
import sys
import asyncio
import signal
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
from config import BOT_TOKEN, LOG_LEVEL
from models import init_db
from handlers.common import start, back_to_main, status
from handlers.firebase_setup import (
    connect_firebase_menu,
    fb_method_callback,
    receive_sa_json,
    receive_sa_url,
    receive_url,
    receive_secret,
    WAITING_SA_JSON,
    WAITING_SA_URL,
    WAITING_URL,
    WAITING_SECRET,
    cancel_conversation,
)
from handlers.devices import (
    manage_devices_menu,
    devices_callback,
    receive_select_device,
    receive_deselect_device,
    WAITING_SELECT,
    WAITING_DESELECT,
)
from handlers.channel import set_channel_start, receive_channel, WAITING_CHANNEL
from handlers.filters_handler import (
    filters_menu,
    filters_callback,
    receive_keyword,
    receive_regex,
    receive_whitelist,
    receive_blacklist,
    WAITING_KEYWORD,
    WAITING_REGEX,
    WAITING_WHITELIST,
    WAITING_BLACKLIST,
)
from handlers.monitoring import (
    start_monitoring,
    stop_monitoring,
    logout,
    on_sms,
    set_runtime,
    restore_active_listeners,
)
from utils.firebase_manager import firebase_manager

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def post_init(application: Application):
    """Called after Application starts – we now have a live event loop."""
    loop = asyncio.get_running_loop()
    set_runtime(application.bot, loop)
    firebase_manager.set_callback(on_sms)
    # Restore any listeners that were active before last restart
    restore_active_listeners()
    logger.info("Bot fully initialised – listeners restored if any")


async def post_shutdown(application: Application):
    """Graceful cleanup on Railway SIGTERM / Ctrl-C."""
    logger.info("Shutting down – stopping all Firebase listeners…")
    firebase_manager.stop_all()


def main():
    init_db()
    logger.info("Database initialised")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ----- Conversations -----
    firebase_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(fb_method_callback, pattern="^(fb_sa|fb_secret)$")
        ],
        states={
            WAITING_SA_JSON: [
                MessageHandler(filters.Document.ALL, receive_sa_json)
            ],
            WAITING_SA_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sa_url)
            ],
            WAITING_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)
            ],
            WAITING_SECRET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_secret)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
        ],
        allow_reentry=True,
    )

    devices_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(devices_callback, pattern="^dev_")],
        states={
            WAITING_SELECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_select_device
                )
            ],
            WAITING_DESELECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_deselect_device
                )
            ],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        allow_reentry=True,
    )

    channel_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📢 Set Channel$"), set_channel_start)
        ],
        states={
            WAITING_CHANNEL: [
                MessageHandler(filters.ALL & ~filters.COMMAND, receive_channel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True,
    )

    filters_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(filters_callback, pattern="^flt_")],
        states={
            WAITING_KEYWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keyword)
            ],
            WAITING_REGEX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_regex)
            ],
            WAITING_WHITELIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_whitelist)
            ],
            WAITING_BLACKLIST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_blacklist)
            ],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        allow_reentry=True,
    )

    # ----- Handlers -----
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.Regex("^🔗 Connect Firebase$"), connect_firebase_menu)
    )
    app.add_handler(
        MessageHandler(filters.Regex("^📱 Manage Devices$"), manage_devices_menu)
    )
    app.add_handler(MessageHandler(filters.Regex("^🔍 Filters$"), filters_menu))
    app.add_handler(MessageHandler(filters.Regex("^📊 Status$"), status))
    app.add_handler(
        MessageHandler(filters.Regex("^▶️ Start Monitoring$"), start_monitoring)
    )
    app.add_handler(
        MessageHandler(filters.Regex("^⏹️ Stop Monitoring$"), stop_monitoring)
    )
    app.add_handler(
        MessageHandler(filters.Regex("^🗑️ Logout / Delete Data$"), logout)
    )

    app.add_handler(firebase_conv)
    app.add_handler(devices_conv)
    app.add_handler(channel_conv)
    app.add_handler(filters_conv)

    # Back button (outside conversations)
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))

    logger.info("Bot starting (polling)…")
    # drop_pending_updates avoids processing a flood of old messages after redeploy
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
