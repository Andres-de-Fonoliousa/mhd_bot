from bot.core.services.mhd_api import MHDAPI


class SyncService:
    def __init__(self):
        self.api = MHDAPI()

    async def sync_prices_to_db(self):
        count = await self.api.sync_all()
        return count

    async def close(self):
        await self.api.close()