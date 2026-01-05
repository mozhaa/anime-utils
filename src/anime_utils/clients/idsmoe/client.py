import json
import time
from pathlib import Path
from typing import Any, Literal, Optional

import aiosqlite

from anime_utils.cache import BaseCacheWithInvalids
from anime_utils.clients.base import HTTPClient
from anime_utils.config import get_settings


class IDsMoeSQLiteCache(BaseCacheWithInvalids[tuple[Any, str], dict]):
    def __init__(self, db_path: Path, ttl: float) -> None:
        self.db_path = db_path
        self.ttl = ttl

    async def __aenter__(self):
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


class IDsMoeClient(HTTPClient):
    """Client for mapping anime IDs via ids.moe API."""

    def __init__(
        self,
        max_rate: Optional[int] = None,
        time_period: Optional[int] = None,
        max_attempts: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        initial_delay: Optional[float] = None,
        base_url: Optional[str] = None,
        socks_url: Optional[str] = None,
        cookies_file: Optional[str] = None,
        cache_db_path: Optional[Path] = None,
        cache_ttl: Optional[float] = None,
        api_key: Optional[str] = None,
    ):
        settings = get_settings()
        if api_key is None:
            api_key = settings.idsmoe_client_settings.api_key
        if cache_db_path is None:
            cache_db_path = Path(settings.cache_dir).expanduser() / settings.idsmoe_client_settings.cache_db_name
        if cache_ttl is None:
            cache_ttl = settings.idsmoe_client_settings.cache_ttl

        self.api_key = api_key
        self._cache_db_path = cache_db_path
        self._cache_ttl = cache_ttl

        super().__init__(
            get_settings().idsmoe_client_settings,
            max_rate,
            time_period,
            max_attempts,
            backoff_factor,
            initial_delay,
            base_url,
            socks_url,
            cookies_file,
        )

    async def __aenter__(self):
        await super().__aenter__()
        self._cache = IDsMoeSQLiteCache(self._cache_db_path, self._cache_ttl)
        await self._cache.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cache.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def get(self, id_: int, platform: str) -> Optional[dict[str, Optional[int | str]]]:
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

        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.get(f"/ids/{id_}?platform={platform}") as response:
                        if response.ok:
                            result = await response.json()
                            await self._cache.set((id_, platform), result)
                            return result
                        return None
