from bot.core.services.api_client import APIClient, MHDAPIError
from bot.core.services.product_service import ProductService
from bot.core.services.order_service import OrderService
from bot.core.services.profile_service import ProfileService


class MHDAPI:
    def __init__(self):
        self._client = APIClient()
        self.products = ProductService(self._client)
        self.orders = OrderService(self._client)
        self.profile = ProfileService(self._client)

    async def sync_all(self):
        return await self.products.sync_products()

    async def close(self):
        await self._client.close()
