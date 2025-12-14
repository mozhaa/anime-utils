from typing import Optional

from aiohttp import ClientSession
from aiolimiter import AsyncLimiter

from .cache import FileCache

default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
}


class CachedHTTPClient:
    def __init__(self, session: ClientSession, cache: FileCache, limiter: AsyncLimiter) -> None:
        self.session = session
        self.cache = cache
        self.limiter = limiter

    async def get(self, url: str, cache_key: Optional[str]) -> str:
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            return cached_data.decode("utf-8")

        async with self.limiter:
            async with self.session.get(url, headers=default_headers) as response:
                response.raise_for_status()
                text = await response.text()

                if cache_key is not None:
                    await self.cache.set(cache_key, text.encode("utf-8"))

                return text
