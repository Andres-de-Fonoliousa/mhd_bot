import os
from dotenv import load_dotenv

# تحميل ملف .env لقراءة المتغيرات منه
load_dotenv()

# الإعدادات العامة للبوت
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) if os.getenv("ADMIN_ID") else 0
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# إعدادات الموقع المصدر الـ API
API_BASE_URL = os.getenv("API_BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")

# نسبة الربح التلقائية لمتجرك (مثلاً 2%)
PROFIT_MARGIN = 1.02