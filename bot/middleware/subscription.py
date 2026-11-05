from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from bot.config import CHANNEL_USERNAME
from bot.bot_instance import get_bot

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if not CHANNEL_USERNAME:
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith('/admin'):
            return await handler(event, data)

        if hasattr(event, 'from_user') and event.from_user:
            chat_id = event.from_user.id
            try:
                bot = get_bot()
                member = await bot.get_chat_member(CHANNEL_USERNAME, chat_id)
                if member.status in ('member', 'administrator', 'creator'):
                    return await handler(event, data)
            except Exception as e:
                print(f"Subscription check failed for {chat_id}: {e}")
                return await handler(event, data)

            msg = f"⚠️ يجب الاشتراك في القناة {CHANNEL_USERNAME} أولاً لاستخدام البوت."
            if isinstance(event, CallbackQuery):
                await event.answer(msg, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(msg)
            return

        return await handler(event, data)
