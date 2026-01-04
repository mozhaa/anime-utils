import json
import logging
from pathlib import Path, PurePosixPath
from typing import Any, Optional, cast
from urllib.parse import parse_qsl, urlparse

from anime_utils.cache import SQLiteCache
from anime_utils.clients.base import HTTPClient
from anime_utils.clients.shikimori.types import ShikimoriAnime
from anime_utils.config import get_settings

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://shikimori.one/api/graphql"
GRAPHQL_ARGS = (
    "id, name, russian, english, japanese, synonyms, "
    "kind, rating, score, status, episodes, duration, "
    "airedOn { year month day }, releasedOn { year month day }, url, "
    "poster { originalUrl mainUrl }, genres { name }, "
    "videos { kind name url playerUrl }, scoresStats { score count }, "
    "statusesStats { status count }, externalLinks { kind url }"
)


def process_anime(anime: dict[str, Any]) -> ShikimoriAnime:
    def set_default[key_t, val_t](obj: dict[key_t, val_t], key: key_t, value: val_t) -> dict[key_t, val_t]:
        if obj.get(key, None) is None:
            obj[key] = value
        return obj

    def set_defaults[key_t, val_t](obj: dict[key_t, val_t], defaults: dict[key_t, val_t]) -> dict[key_t, val_t]:
        for key, value in defaults.items():
            obj = set_default(obj, key, value)
        return obj

    anime = set_default(
        anime,
        "poster",
        {
            "originalUrl": "https://shikimori.one/assets/globals/missing/main.png",
            "mainUrl": "https://shikimori.one/assets/globals/missing/preview_animanga.png",
        },
    )

    anime["statusesStats"] = set_defaults(
        dict(map(lambda x: x.values(), anime["statusesStats"])),
        {
            "planned": 0,
            "completed": 0,
            "watching": 0,
            "dropped": 0,
            "on_hold": 0,
        },
    )

    anime["scoresStats"] = set_defaults(
        dict(map(lambda x: x.values(), anime["scoresStats"])),
        {i: 0 for i in range(1, 11)},
    )

    anidb_url = next(iter([x["url"] for x in anime["externalLinks"] if "anidb.net" in x["url"]]), None)
    anime["anidb_id"] = get_anidb_id(anidb_url) if anidb_url is not None else None
    anime["id"] = int(anime["id"])

    return cast(ShikimoriAnime, anime)


def get_anidb_id(url: str) -> int:
    parsed_url = urlparse(url)
    path = PurePosixPath(parsed_url.path)
    if path.parts[-1].isdigit():
        return int(path.parts[-1])
    if path.parts[-1] == "animedb.pl":
        query_params = dict(parse_qsl(parsed_url.query))
        if "aid" in query_params:
            return int(query_params["aid"])
    logger.warning(f"cannot parse anidb_id from anidb_url: {url}")
    raise RuntimeError(f"Cannot parse anidb_id from anidb_url: {url}!")


class ShikimoriClient(HTTPClient):
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
    ):
        settings = get_settings()
        if cache_db_path is None:
            cache_db_path = Path(settings.cache_dir).expanduser() / settings.shikimori_client_settings.cache_db_name
        if cache_ttl is None:
            cache_ttl = settings.shikimori_client_settings.cache_ttl

        self._cache_db_path = cache_db_path
        self._cache_ttl = cache_ttl

        super().__init__(
            settings.shikimori_client_settings,
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
        self._cache = SQLiteCache(self._cache_db_path, self._cache_ttl)
        await self._cache.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cache.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def get_anime(self, mal_id: int) -> Optional[ShikimoriAnime]:
        cache_key = f"anime:{mal_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return json.loads(cached)

        logger.info(f"fetching anime with mal_id: {mal_id}")
        query = f'{{ animes(ids: "{mal_id}", limit: 1) {{ {GRAPHQL_ARGS} }} }}'
        body = {"operationName": None, "query": query, "variables": {}}

        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.post(url=GRAPHQL_URL, json=body) as response:
                        data = json.loads(await response.text())
        animes = data["data"]["animes"]
        result = process_anime(animes[0]) if len(animes) > 0 else None
        if result is not None:
            await self._cache.set(cache_key, json.dumps(result))
        return result

    async def search(self, query: str, limit: int = 10) -> list[ShikimoriAnime]:
        logger.info(f"searching anime with query: {query}, limit: {limit}")
        query = f'{{ animes(search: "{query}", limit: {limit}) {{ {GRAPHQL_ARGS} }} }}'
        body = {"operationName": None, "query": query, "variables": {}}

        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.post(url=GRAPHQL_URL, json=body) as response:
                        data = json.loads(await response.text())
        return list(map(process_anime, data["data"]["animes"]))
