from bot.core.services.api_client import APIClient


class ProfileService:
    def __init__(self, api_client: APIClient = None):
        self.api = api_client or APIClient()

    async def get_balance(self):
        profile = await self.api.get_profile()
        return float(profile.get("balance", 0))

    async def get_profile(self):
        return await self.api.get_profile()
