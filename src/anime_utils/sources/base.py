import logging
from pathlib import Path
from typing import Optional

import aiohttp
from aiolimiter import AsyncLimiter

from anime_utils.utils import AioCookieJar

from ..cache import FileCache
from ..http import CachedHTTPClient, default_headers

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(
        self,
        cache_dir: str,
        max_rate: int,
        time_period: int,
        base_url: str,
        socks_url: Optional[str],
        cookies_file: Optional[str] = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.max_rate = max_rate
        self.time_period = time_period
        self.base_url = base_url
        self.socks_url = socks_url
        self.cookies_file = cookies_file

        self._session: aiohttp.ClientSession | None = None
        self._limiter: AsyncLimiter | None = None
        self._cache: FileCache | None = None
        self._http_client: CachedHTTPClient | None = None
        self._cookie_jar: AioCookieJar | None = None

    async def __aenter__(self):
        connector = None
        if self.socks_url:
            from aiohttp_socks import ProxyConnector

            logger.info(f"using socks proxy by url: {self.socks_url}")
            connector = ProxyConnector.from_url(self.socks_url)

        if self.cookies_file:
            cookies_path = Path(self.cookies_file)
            self._cookie_jar = AioCookieJar(cookies_path)
            if cookies_path.exists():
                try:
                    self._cookie_jar.load()
                except Exception as e:
                    logger.warning(f"failed to load cookies from {self.cookies_file}: {e}")
        else:
            self._cookie_jar = None

        self._session = aiohttp.ClientSession(
            base_url=self.base_url, headers=default_headers, connector=connector, cookie_jar=self._cookie_jar
        )
        self._limiter = AsyncLimiter(self.max_rate, self.time_period)
        self._cache = FileCache(self.cache_dir)
        self._http_client = CachedHTTPClient(self._session, self._cache, self._limiter)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
