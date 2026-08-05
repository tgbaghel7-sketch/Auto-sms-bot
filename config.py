import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SQLITE_PATH = os.getenv("SQLITE_PATH", "bot.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Get it from @BotFather on Telegram.")

if DATABASE_URL is not None and str(DATABASE_URL).strip() == "":
    DATABASE_URL = None
