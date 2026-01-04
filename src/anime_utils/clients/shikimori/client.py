import json
import logging
from pathlib import PurePosixPath
from typing import Any, Optional
from urllib.parse import parse_qsl, urlparse

from aiohttp import ClientSession

from anime_utils.clients.base import BaseClient
from anime_utils.config import get_settings
from anime_utils.http import default_headers

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


def process_anime(anime: dict[str, Any]) -> dict[str, Any]:
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
    ).items()

    anime["scoresStats"] = set_defaults(
        dict(map(lambda x: x.values(), anime["scoresStats"])),
        {i: 0 for i in range(1, 11)},
    ).items()

    anidb_url = next(iter([x["url"] for x in anime["externalLinks"] if "anidb.net" in x["url"]]), None)
    anime["anidb_id"] = get_anidb_id(anidb_url) if anidb_url is not None else None
    anime["id"] = int(anime["id"])

    return anime


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


class ShikimoriClient(BaseClient):
    def __init__(
        self,
        max_rate: Optional[int] = None,
        time_period: Optional[int] = None,
        max_attempts: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        initial_delay: Optional[float] = None,
    ):
        settings = get_settings()
        if max_rate is None:
            max_rate = settings.shikimori_client_settings.rate_limit.max_rate
        if time_period is None:
            time_period = settings.shikimori_client_settings.rate_limit.time_period
        if max_attempts is None:
            max_attempts = settings.shikimori_client_settings.retry_settings.max_attempts
        if backoff_factor is None:
            backoff_factor = settings.shikimori_client_settings.retry_settings.backoff_factor
        if initial_delay is None:
            initial_delay = settings.shikimori_client_settings.retry_settings.initial_delay

        from aiolimiter import AsyncLimiter
        from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

        self._limiter = AsyncLimiter(max_rate=max_rate, time_period=time_period)
        self._retry = AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor, min=initial_delay),
            retry=retry_if_exception_type((json.JSONDecodeError,)),
        )
        self._session = ClientSession(headers=default_headers)

    async def __aenter__(self):
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()

    async def get_anime(self, mal_id: int) -> Optional[dict[str, Any]]:
        logger.info(f"fetching anime with mal_id: {mal_id}")
        query = f'{{ animes(ids: "{mal_id}", limit: 1) {{ {GRAPHQL_ARGS} }} }}'
        body = {"operationName": None, "query": query, "variables": {}}

        async def _fetch() -> Optional[dict[str, Any]]:
            async with self._session.post(url=GRAPHQL_URL, json=body) as response:
                data = json.loads(await response.text())
            animes = data["data"]["animes"]
            return process_anime(animes[0]) if len(animes) > 0 else None

        return await self._retry(_fetch)

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        logger.info(f"searching anime with query: {query}, limit: {limit}")
        query = f'{{ animes(search: "{query}", limit: {limit}) {{ {GRAPHQL_ARGS} }} }}'
        body = {"operationName": None, "query": query, "variables": {}}

        async def _fetch() -> list[dict[str, Any]]:
            async with self._session.post(url=GRAPHQL_URL, json=body) as response:
                data = json.loads(await response.text())
            return list(map(process_anime, data["data"]["animes"]))

        return await self._retry(_fetch)
