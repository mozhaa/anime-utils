from contextlib import AsyncExitStack
from typing import Any, Optional, Self

from aiohttp import ClientSession
from aiolimiter import AsyncLimiter

from anime_utils.clients.base import BaseClient
from anime_utils.config import get_settings
from anime_utils.http import default_headers


class IDsMoeClient(BaseClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_rate: Optional[int] = None,
        time_period: Optional[int] = None,
    ):
        settings = get_settings()
        if api_key is None:
            api_key = settings.idsmoe_client_settings.api_key
        if max_rate is None:
            max_rate = settings.idsmoe_client_settings.rate_limit.max_rate
        if time_period is None:
            time_period = settings.idsmoe_client_settings.rate_limit.time_period

        self.api_key = api_key
        self._limiter = AsyncLimiter(max_rate=max_rate, time_period=time_period)

    async def __aenter__(self) -> Self:
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        headers = default_headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        self._session = ClientSession(base_url="https://api.ids.moe", headers=headers)
        await self._stack.enter_async_context(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._stack.__aexit__(exc_type, exc_val, exc_tb)

    async def get(self, id_: int, platform: str) -> Optional[dict[str, Any]]:
        async with self._session.get(f"/ids/{id_}?platform={platform}") as response:
            if response.ok:
                return await response.json()
