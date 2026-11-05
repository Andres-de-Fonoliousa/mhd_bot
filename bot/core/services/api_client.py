import aiohttp
import asyncio
from bot.config import API_BASE_URL, API_TOKEN


class MHDAPIError(Exception):
    def __init__(self, message, code=None, data=None):
        super().__init__(message)
        self.code = code
        self.data = data


class InsufficientBalanceError(MHDAPIError):
    pass


class DuplicateOrderError(MHDAPIError):
    def __init__(self, message, wait_seconds=60, **kwargs):
        super().__init__(message, code=429, **kwargs)
        self.wait_seconds = wait_seconds


class APIClient:
    BASE = API_BASE_URL.rstrip("/") 

    def __init__(self, token=None):
        self._token = token or API_TOKEN
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"api-token": self._token},
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _request(self, method, path, **kwargs):
        url = f"{self.BASE}{path}"
        session = await self._get_session()
        retries = 3
        last_error = None

        for attempt in range(retries):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    body = await resp.json()

                    if resp.status == 402:
                        raise InsufficientBalanceError(
                            body.get("message", "Insufficient balance"),
                            code=402,
                            data=body,
                        )

                    if resp.status == 429:
                        raise DuplicateOrderError(
                            body.get("message", "Duplicate order"),
                            wait_seconds=body.get("wait_seconds", 60),
                            code=429,
                            data=body,
                        )

                    if resp.status >= 400:
                        raise MHDAPIError(
                            body.get("message", f"HTTP {resp.status}"),
                            code=resp.status,
                            data=body,
                        )

                    return body

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                continue

        raise MHDAPIError(f"Request failed after {retries} retries: {last_error}")

    async def get_products(self):
        return await self._request("GET", "/client/api/products")

    async def create_order(self, product_id, qty, player_id, order_uuid, any_key=None):
        params = {
            "qty": str(qty),
            "playerId": str(player_id),
            "order_uuid": order_uuid,
        }
        if any_key is not None:
            params["anyKey"] = str(any_key)

        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return await self._request(
            "GET",
            f"/client/api/newOrder/{product_id}/params?{qs}",
        )

    async def check_order(self, order_id):
        return await self._request(
            "GET",
            f"/client/api/check?orders=[{order_id}]&uuid=1",
        )

    async def get_profile(self):
        return await self._request("GET", "/client/api/profile")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
