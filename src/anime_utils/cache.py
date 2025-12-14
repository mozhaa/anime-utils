import logging
import re
import zlib
from pathlib import Path
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)


class FileCache:
    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir).expanduser()
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        logger.debug(f"creating cache directory {self.cache_dir}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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

    async def set(self, key: str, data: bytes) -> None:
        cache_path = self._get_cache_path(key)

        try:
            compressed_data = zlib.compress(data)
            async with aiofiles.open(cache_path, "wb+") as f:
                await f.write(compressed_data)
        except zlib.error as e:
            logger.warning(f"failed to write cache file {cache_path}: {e}")
