import logging
import sys
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters,
)
from config import BOT_TOKEN, LOG_LEVEL
from models import init_db
from handlers.common import start, back_to_main, status
from handlers.firebase_handler import (
    firebase_menu, fb_callback,
    receive_name, receive_public_url, receive_sa_json, receive_sa_url,
    receive_secret_url, receive_secret_key, cancel,
    WAIT_NAME, WAIT_URL_PUBLIC, WAIT_SA_JSON, WAIT_SA_URL,
    WAIT_SECRET_URL, WAIT_SECRET_KEY,
)
from handlers.devices_handler import (
    devices_menu, devices_callback,
    receive_add_device, receive_remove_device,
    WAITING_ADD, WAITING_REMOVE,
)
from handlers.channel_handler import (
    channel_menu, channel_callback, receive_channel, WAITING_CHANNEL,
)
from handlers.filters_handler import (
    filters_menu, filters_callback,
    receive_kw, receive_re, receive_wl, receive_bl,
    WAITING_KW, WAITING_RE, WAITING_WL, WAITING_BL,
)
from handlers.monitoring import (
    start_forwarding, stop_forwarding, on_sms, set_runtime, restore_active_listeners,
)
from utils.firebase_manager import firebase_manager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def post_init(application: Application):
    loop = asyncio.get_running_loop()
    set_runtime(application.bot, loop)
    firebase_manager.set_callback(on_sms)
    restore_active_listeners()
    logger.info("Bot ready – listeners restored if any")


async def post_shutdown(application: Application):
    logger.info("Shutting down…")
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

    # ── Firebase add conversation ──
    fb_add_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                fb_callback,
                pattern="^(fbtype_public|fbtype_sa|fbtype_secret)$",
            )
        ],
        states={
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WAIT_URL_PUBLIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_public_url)],
            WAIT_SA_JSON: [MessageHandler(filters.Document.ALL, receive_sa_json)],
            WAIT_SA_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sa_url)],
            WAIT_SECRET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_secret_url)],
            WAIT_SECRET_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_secret_key)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(fb_callback, pattern="^fb_menu$"),
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
        ],
        allow_reentry=True,
    )

    # ── Devices conversation ──
    devices_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(devices_callback, pattern="^dev_")],
        states={
            WAITING_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_add_device)],
            WAITING_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_remove_device)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        allow_reentry=True,
    )

    # ── Channel conversation ──
    channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(channel_callback, pattern="^ch_add$")],
        states={
            WAITING_CHANNEL: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_channel)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
        ],
        allow_reentry=True,
    )

    # ── Filters conversation ──
    filters_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(filters_callback, pattern="^flt_")],
        states={
            WAITING_KW: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_kw)],
            WAITING_RE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_re)],
            WAITING_WL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wl)],
            WAITING_BL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bl)],
        },
        fallbacks=[CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        allow_reentry=True,
    )

    # ── Handlers ──
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🔥 Manage Firebase$"), firebase_menu))
    app.add_handler(MessageHandler(filters.Regex("^📱 Device$"), devices_menu))
    app.add_handler(MessageHandler(filters.Regex("^📢 Manage Channel$"), channel_menu))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Filters$"), filters_menu))
    app.add_handler(MessageHandler(filters.Regex("^📊 Status$"), status))
    app.add_handler(MessageHandler(filters.Regex("^▶️ Start Forwarding$"), start_forwarding))
    app.add_handler(MessageHandler(filters.Regex("^⏹ Stop Forwarding$"), stop_forwarding))

    app.add_handler(fb_add_conv)
    app.add_handler(devices_conv)
    app.add_handler(channel_conv)
    app.add_handler(filters_conv)

    # Remaining firebase / channel callbacks (list, select, delete, menu)
    app.add_handler(CallbackQueryHandler(fb_callback, pattern="^fb_"))
    app.add_handler(CallbackQueryHandler(channel_callback, pattern="^ch_"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))

    logger.info("Bot starting…")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
