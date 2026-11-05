import asyncio
import sys
import os

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from aiogram.types import BotCommand
from bot.bot_instance import init_bot
from bot.config import ADMIN_ID, CHANNEL_USERNAME
from bot.core.database import init_db
from bot.handlers.user_handler import router as user_router
from bot.handlers.admin_handler import router as admin_router
from bot.middleware.subscription import SubscriptionMiddleware

bot, dp = init_bot()

dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

dp.include_router(user_router)
dp.include_router(admin_router)

async def periodic_sync():
    while True:
        try:
            from bot.core.services.mhd_api import MHDAPI
            api = MHDAPI()
            count = await api.sync_all()
            print(f"Synced {count} products from MHD API.")
            await api.close()
        except Exception as e:
            print(f"Sync error: {e}")
        await asyncio.sleep(21600)  # every 6 hours

async def main():
    print("Starting bot...")
    init_db()

    # Initial product sync
    try:
        from bot.core.services.mhd_api import MHDAPI
        api = MHDAPI()
        count = await api.sync_all()
        print(f"Initial sync: {count} products loaded.")
        await api.close()
    except Exception as e:
        print(f"Initial sync skipped: {e}")

    # Periodic sync background task
    asyncio.create_task(periodic_sync())

    commands = [
        BotCommand(command="start", description="home / القائمة الرئيسية"),
        BotCommand(command="admin", description="admins only / للادمن فقط"),
    ]
    await bot.set_my_commands(commands)

    print(f"Bot started successfully! Admin ID: {ADMIN_ID}")
    print(f"Channel: {CHANNEL_USERNAME}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
