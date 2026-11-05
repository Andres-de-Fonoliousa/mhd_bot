from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.config import BOT_TOKEN

bot: Bot = None
dp: Dispatcher = None

def init_bot():
    global bot, dp
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    return bot, dp

def get_bot() -> Bot:
    return bot

def get_dispatcher() -> Dispatcher:
    return dp
