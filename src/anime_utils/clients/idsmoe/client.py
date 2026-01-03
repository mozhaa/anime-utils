import json
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Literal, Optional, Self

import aiohttp
import aiosqlite
from aiohttp import ClientSession
from aiolimiter import AsyncLimiter
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from anime_utils.cache import BaseCacheWithInvalids
from anime_utils.clients.base import BaseClient
from anime_utils.config import get_settings
from anime_utils.http import default_headers


class IDsMoeSQLiteCache(BaseCacheWithInvalids[tuple[Any, str], dict]):
    def __init__(self, db_path: Path, ttl: float) -> None:
        self.db_path = db_path
        self.ttl = ttl

    async def __aenter__(self) -> Self:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute(
            "CREATE TABLE IF NOT EXISTS id_mappings "
            "(platform TEXT, id TEXT, anidb_id INTEGER, timestamp REAL, PRIMARY KEY (platform, id))"
        )
        await self.db.execute(
            "CREATE TABLE IF NOT EXISTS anime_data (anidb_id INTEGER PRIMARY KEY, json_data TEXT, timestamp REAL)"
        )
        await self.db.commit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.db.close()

    async def get(self, key: tuple[Any, str]) -> Optional[dict | Literal[False]]:
        id_, platform = key
        cursor = await self.db.execute(
            "SELECT anidb_id, timestamp FROM id_mappings WHERE platform = ? AND id = ?", (platform, str(id_))
        )
        row = await cursor.fetchone()
        await cursor.close()
        if not row:
            return None

        anidb_id, timestamp = row
        if time.time() - timestamp > self.ttl:
            await self.db.execute("DELETE FROM id_mappings WHERE platform = ? AND id = ?", (platform, str(id_)))
            if anidb_id is not None:
                await self.db.execute("DELETE FROM anime_data WHERE anidb_id = ?", (anidb_id,))
            await self.db.commit()
            return None

        if anidb_id is None:
            return False

        cursor = await self.db.execute("SELECT json_data FROM anime_data WHERE anidb_id = ?", (anidb_id,))
        data_row = await cursor.fetchone()
        await cursor.close()
        if not data_row:
            await self.db.execute("DELETE FROM id_mappings WHERE anidb_id = ?", (anidb_id,))
            await self.db.commit()
            return None

        return json.loads(data_row[0])

    async def set(self, key: tuple[Any, str], value: dict | Literal[False]) -> None:
        id_, platform = key
        timestamp = time.time()

        if value is False:
            await self.db.execute(
                "INSERT OR REPLACE INTO id_mappings (platform, id, anidb_id, timestamp) VALUES (?, ?, NULL, ?)",
                (platform, str(id_), timestamp),
            )
            await self.db.commit()
            return

        anidb_id = value.get("anidb")
        if anidb_id is None:
            return

        serialized_value = json.dumps(value)
        await self.db.execute(
            "INSERT OR REPLACE INTO anime_data (anidb_id, json_data, timestamp) VALUES (?, ?, ?)",
            (anidb_id, serialized_value, timestamp),
        )
        await self.db.execute(
            "INSERT OR REPLACE INTO id_mappings (platform, id, anidb_id, timestamp) VALUES (?, ?, ?, ?)",
            (platform, str(id_), anidb_id, timestamp),
        )
        for p, pid in value.items():
            if p == "title" or pid is None or p == platform:
                continue
            await self.db.execute(
                "INSERT OR REPLACE INTO id_mappings (platform, id, anidb_id, timestamp) VALUES (?, ?, ?, ?)",
                (p, str(pid), anidb_id, timestamp),
            )
        await self.db.commit()


class IDsMoeClient(BaseClient):
    """Client for mapping anime IDs via ids.moe API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_rate: Optional[int] = None,
        time_period: Optional[int] = None,
        cache_db_path: Optional[Path] = None,
        cache_ttl: Optional[float] = None,
        max_attempts: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        initial_delay: Optional[float] = None,
    ):
        """Initialize the IDsMoe client.

        Args:
            api_key: API key for authentication
            max_rate: Maximum number of requests per time period
            time_period: Time period in seconds for rate limiting
            cache_db_path: Path to SQLite cache database
            cache_ttl: Cache time-to-live in seconds
            max_attempts: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            initial_delay: Initial delay for retry in seconds
        """
        settings = get_settings()
        if api_key is None:
            api_key = settings.idsmoe_client_settings.api_key
        if max_rate is None:
            max_rate = settings.idsmoe_client_settings.rate_limit.max_rate
        if time_period is None:
            time_period = settings.idsmoe_client_settings.rate_limit.time_period
        if cache_db_path is None:
            cache_db_path = Path(settings.cache_dir).expanduser() / settings.idsmoe_client_settings.cache_db_name
        if cache_ttl is None:
            cache_ttl = settings.idsmoe_client_settings.cache_ttl
        if max_attempts is None:
            max_attempts = settings.idsmoe_client_settings.retry_settings.max_attempts
        if backoff_factor is None:
            backoff_factor = settings.idsmoe_client_settings.retry_settings.backoff_factor
        if initial_delay is None:
            initial_delay = settings.idsmoe_client_settings.retry_settings.initial_delay

        self.api_key = api_key
        self._limiter = AsyncLimiter(max_rate=max_rate, time_period=time_period)
        self._retry = AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor, min=initial_delay),
            retry=retry_if_exception_type((aiohttp.ClientError, aiohttp.ClientResponseError)),
        )

        headers = default_headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        self._session = ClientSession(base_url="https://api.ids.moe", headers=headers)

        self._cache = IDsMoeSQLiteCache(cache_db_path, cache_ttl)

    async def __aenter__(self) -> Self:
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        await self._stack.enter_async_context(self._cache)
        await self._stack.enter_async_context(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._stack.__aexit__(exc_type, exc_val, exc_tb)

    async def get(self, id_: int, platform: str) -> Optional[dict[str, Any]]:
        """Get anime information and ID mappings for a given ID and platform.

        Args:
            id_: The anime ID to look up.
            platform: The platform of the ID (e.g., "anidb", "anilist", "myanimelist", "shikimori").

        Returns:
            A dictionary containing anime information with ID mappings across platforms,
            including keys like "title", "anidb", "anilist", "myanimelist", etc.
            Returns None if the ID is not found.
        """
        result = await self._cache.get((id_, platform))
        if result is not None:
            return result or None

        async def _fetch() -> Optional[dict[str, Any]]:
            async with self._session.get(f"/ids/{id_}?platform={platform}") as response:
                if response.ok:
                    result = await response.json()
                    await self._cache.set((id_, platform), result)
                    return result
                return None

        return await (await self._retry(_fetch))
