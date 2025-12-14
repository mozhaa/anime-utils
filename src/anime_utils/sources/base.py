import logging
from typing import Optional

from aiohttp import ClientSession
from aiolimiter import AsyncLimiter

from ..cache import FileCache
from ..http import CachedHTTPClient, default_headers

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(
        self, cache_dir: str, max_rate: int, time_period: int, base_url: str, socks_url: Optional[str]
    ) -> None:
        self.cache_dir = cache_dir
        self.max_rate = max_rate
        self.time_period = time_period
        self.base_url = base_url
        self.socks_url = socks_url

        self._session: ClientSession | None = None
        self._limiter: AsyncLimiter | None = None
        self._cache: FileCache | None = None
        self._http_client: CachedHTTPClient | None = None

    async def __aenter__(self):
        connector = None
        if self.socks_url:
            from aiohttp_socks import ProxyConnector

            logger.info(f"using socks proxy by url: {self.socks_url}")
            connector = ProxyConnector.from_url(self.socks_url)

        self._session = ClientSession(base_url=self.base_url, headers=default_headers, connector=connector)
        self._limiter = AsyncLimiter(self.max_rate, self.time_period)
        self._cache = FileCache(self.cache_dir)
        self._http_client = CachedHTTPClient(self._session, self._cache, self._limiter)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
