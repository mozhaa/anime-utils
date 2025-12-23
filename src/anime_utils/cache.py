import logging
import re
import zlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Self

import aiofiles

logger = logging.getLogger(__name__)


class BaseCache[key_t, val_t](ABC):
    @abstractmethod
    async def __aenter__(self) -> Self:
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    @abstractmethod
    async def get(self, key: key_t) -> Optional[val_t]:
        pass

    @abstractmethod
    async def set(self, key: key_t, value: val_t) -> None:
        pass


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
