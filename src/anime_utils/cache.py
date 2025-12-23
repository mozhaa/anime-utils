import logging
import re
import zlib
from abc import abstractmethod
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Literal, Optional, Self

import aiofiles
import aiosqlite

logger = logging.getLogger(__name__)


class BaseCache[key_t, val_t](AbstractAsyncContextManager):
    @abstractmethod
    async def get(self, key: key_t) -> Optional[val_t]:
        pass

    @abstractmethod
    async def set(self, key: key_t, value: val_t) -> None:
        pass


class BaseCacheWithInvalids[key_t, val_t](BaseCache[key_t, val_t | Literal[False]]):
    @abstractmethod
    async def get(self, key: key_t) -> Optional[val_t | Literal[False]]:
        pass

    @abstractmethod
    async def set(self, key: key_t, value: val_t | Literal[False]) -> None:
        pass


class SQLiteCache(BaseCache[str, str]):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    async def __aenter__(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
        await self.db.commit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def get(self, key: str) -> Optional[str]:
        cursor = await self.db.execute("SELECT value FROM cache WHERE key = ?", (key,))
        row = await cursor.fetchone()
        await cursor.close()
        return row[0] if row else None

    async def set(self, key: str, value: str) -> None:
        await self.db.execute("INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", (key, value))
        await self.db.commit()


class FileCache(BaseCache[str, bytes]):
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    async def __aenter__(self) -> Self:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def _get_cache_path(self, key: str) -> Path:
        m = re.search(r'[<>:"/\\|?*]', key)
        if m is not None:
            raise ValueError(f"invalid character in cache key: {m.group(0)}")
        return self.cache_dir / f"{key}.html.zlib"

    async def get(self, key: str) -> Optional[bytes]:
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            async with aiofiles.open(cache_path, "rb") as f:
                compressed_data = await f.read()
                return zlib.decompress(compressed_data)
        except zlib.error as e:
            logger.warning(f"failed to decompress data from cached file, removing {cache_path}: {e}")
            cache_path.unlink()
            return None

    async def set(self, key: str, value: bytes) -> None:
        cache_path = self._get_cache_path(key)

        try:
            compressed_data = zlib.compress(value)
            async with aiofiles.open(cache_path, "wb+") as f:
                await f.write(compressed_data)
        except zlib.error as e:
            logger.warning(f"failed to write cache file {cache_path}: {e}")
