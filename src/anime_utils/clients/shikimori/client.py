import json
import logging
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Optional
from urllib.parse import parse_qsl, urlparse

from anime_utils._cache import SQLiteCache
from anime_utils._config import get_settings
from anime_utils.clients.base import HTTPClient
from anime_utils.clients.shikimori.types import ShikimoriAnime, ShikimoriExternalLink, ShikimoriVideo

logger = logging.getLogger(__name__)

GRAPHQL_URL = "/api/graphql"
GRAPHQL_ARGS = (
    "id, name, russian, english, japanese, synonyms, "
    "kind, rating, score, status, episodes, duration, "
    "airedOn { year month day }, releasedOn { year month day }, url, "
    "poster { originalUrl mainUrl }, genres { name }, "
    "videos { kind name url playerUrl }, scoresStats { score count }, "
    "statusesStats { status count }, externalLinks { kind url }"
)
DEFAULT_ORIGINAL_POSTER_URL = "https://shikimori.one/assets/globals/missing/main.png"
DEFAULT_MAIN_POSTER_URL = "https://shikimori.one/assets/globals/missing/preview_animanga.png"


def _format_date(date_data: Optional[dict[str, int]]) -> str:
    if not date_data:
        return ""
    try:
        return date(date_data["year"], date_data["month"], date_data["day"]).strftime("%Y-%m-%d")
    except (ValueError, TypeError, KeyError):
        return ""


def process_anime(anime: dict[str, Any]) -> ShikimoriAnime:
    anidb_url = next((link["url"] for link in anime.get("externalLinks", []) if link["kind"] == "anime_db"), None)
    scores = {score: 0 for score in range(1, 11)}
    scores.update({int(item["score"]): item["count"] for item in anime.get("scoresStats", [])})
    statuses = {status: 0 for status in ["planned", "completed", "watching", "dropped", "on_hold"]}
    statuses.update({item["status"]: item["count"] for item in anime.get("statusesStats", [])})
    return ShikimoriAnime(
        id=int(anime["id"]),
        name=anime["name"],
        russian=anime["russian"],
        english=anime.get("english"),
        japanese=anime.get("japanese"),
        synonyms=anime.get("synonyms", []),
        kind=anime["kind"],
        rating=anime.get("rating"),
        score=anime.get("score"),
        status=anime["status"],
        episodes=anime.get("episodes"),
        duration=anime.get("duration"),
        aired_on=_format_date(anime.get("airedOn")),
        released_on=_format_date(anime.get("releasedOn")),
        url=anime["url"],
        poster_original_url=anime["poster"]["originalUrl"] if "poster" in anime else DEFAULT_ORIGINAL_POSTER_URL,
        poster_main_url=anime["poster"]["mainUrl"] if "poster" in anime else DEFAULT_MAIN_POSTER_URL,
        genres=[g["name"] for g in anime.get("genres", [])],
        videos=[
            ShikimoriVideo(kind=v["kind"], name=v["name"], url=v["url"], player_url=v["playerUrl"])
            for v in anime.get("videos", [])
        ],
        scores_stats=scores,
        statuses_stats=statuses,
        external_links=[
            ShikimoriExternalLink(kind=link["kind"], url=link["url"]) for link in anime.get("externalLinks", [])
        ],
        anidb_id=get_anidb_id(anidb_url) if anidb_url is not None else None,
    )


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
    """Client for accessing Shikimori GraphQL API."""

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
        timeout: Optional[float] = None,
        cache_db_path: Optional[Path] = None,
        cache_ttl: Optional[float] = None,
    ):
        settings = get_settings()
        if cache_db_path is None:
            cache_db_path = Path(settings.cache_dir).expanduser() / settings.shikimori_client_settings.cache_db_name
        if cache_ttl is None:
            cache_ttl = settings.shikimori_client_settings.cache_ttl
        if base_url is None:
            base_url = "https://shikimori.one"

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
            timeout,
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
        """Get anime information from Shikimori by MyAnimeList ID (the same as Shikimori ID).

        Args:
            mal_id: The MyAnimeList anime ID

        Returns:
            Anime information or None if not found
        """
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
        """Search for anime on Shikimori.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of anime matching the search query
        """
        logger.info(f"searching anime with query: {query}, limit: {limit}")
        query = f'{{ animes(search: "{query}", limit: {limit}) {{ {GRAPHQL_ARGS} }} }}'
        body = {"operationName": None, "query": query, "variables": {}}

        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.post(url=GRAPHQL_URL, json=body) as response:
                        data = json.loads(await response.text())
        return list(map(process_anime, data["data"]["animes"]))
