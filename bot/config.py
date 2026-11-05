import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else 0
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

API_BASE_URL = os.getenv("API_BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")

USD_TO_LIRA_RATE = float(os.getenv("USD_TO_LIRA_RATE", 170))

PROFIT_MARGIN_FF_GEMS = float(os.getenv("PROFIT_MARGIN_FF_GEMS", 1.02))
PROFIT_MARGIN_PUBG_UC = float(os.getenv("PROFIT_MARGIN_PUBG_UC", 1.02))
PROFIT_MARGIN_FF_SUBS = float(os.getenv("PROFIT_MARGIN_FF_SUBS", 1.02))

PROFIT_MARGIN = 1.02
