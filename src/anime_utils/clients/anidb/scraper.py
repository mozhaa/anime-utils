import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import quote, urlencode

from anime_utils._cache import FileCache
from anime_utils._config import get_settings
from anime_utils.clients.anidb.core import (
    get_characters,
    get_main_info,
    get_search_results,
    get_similar,
    get_songs,
    get_tags,
)
from anime_utils.clients.anidb.types import (
    AniDBCharacter,
    AniDBMainInfo,
    AniDBSearchResult,
    AniDBSimilarAnime,
    AniDBSong,
    AniDBTags,
)
from anime_utils.clients.base import HTTPClient

logger = logging.getLogger(__name__)


class AniDBScraper(HTTPClient):
    """Client for scraping AniDB anime information."""

    name = "anidb"

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
        cache_dir: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        if cache_dir is None:
            cache_dir = settings.cache_dir
        if base_url is None:
            base_url = "https://anidb.net"

        self._cache_dir = Path(cache_dir).expanduser()
        super().__init__(
            get_settings().anidb_scraper_settings,
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
        self._cache = FileCache(self._cache_dir)
        return self

    async def _fetch_page(self, cache_key: str, url: str) -> str:
        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(f"cache hit for {cache_key}")
            return cached.decode("utf-8")

        logger.info(f"cache miss for {cache_key}")
        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.get(url) as response:
                        response.raise_for_status()
                        text = await response.text()

        await self._cache.set(cache_key, text.encode("utf-8"))
        return text

    async def get_tags(self, anime_id: int, with_descriptions: bool = False) -> AniDBTags:
        """Get tags for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID
            with_descriptions: Write description for each tag

        Returns:
            List of tags for anime
        """
        text = await self._fetch_page(f"anidb-{anime_id}", f"/anime/{anime_id}")
        tags = get_tags(text)
        if not with_descriptions:

            def remove_descriptions(obj: Any) -> None:
                if isinstance(obj, list):
                    for child in obj:
                        remove_descriptions(child)
                elif isinstance(obj, dict):
                    if "description" in obj:
                        obj.pop("description")
                    for value in obj.values():
                        remove_descriptions(value)

            remove_descriptions(tags)
        return tags

    async def get_main_info(self, anime_id: int) -> AniDBMainInfo:
        """Get main information for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            Main information about the anime
        """
        text = await self._fetch_page(f"anidb-{anime_id}", f"/anime/{anime_id}")
        return get_main_info(text)

    async def get_characters(self, anime_id: int) -> list[AniDBCharacter]:
        """Get character information for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of characters in the anime
        """
        text = await self._fetch_page(f"anidb-{anime_id}", f"/anime/{anime_id}")
        return get_characters(text)

    async def get_similar(self, anime_id: int) -> list[AniDBSimilarAnime]:
        """Get similar anime recommendations from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of similar anime
        """
        text = await self._fetch_page(f"anidb-{anime_id}", f"/anime/{anime_id}")
        return get_similar(text)

    async def search_by_tags(
        self,
        atags_include: str = "",
        atags_exclude: str = "",
        etags_include: str = "",
        etags_exclude: str = "",
        ctags_include: str = "",
        ctags_exclude: str = "",
        order_by: Literal["name", "rating", "average", "ucnt", "airdate", "enddate"] = "name",
        order_direction: Literal["asc", "desc"] = "asc",
        limit: Optional[int] = None,
    ) -> list[AniDBSearchResult]:
        """Search for anime on AniDB using tag-based filtering.

        AniDB categorizes tags into three distinct types:
        1. **Anime Tags**: Describe overall themes, genres, and features.
        - Range from general (action, comedy) to specific (cyberpunk, parental abandonment).
        - Most anime tags have a weight (0.5-3 stars) indicating relevance, but some tags
            (e.g., "male protagonist") are weightless and treated as boolean flags.
        2. **Episode Tags**: Describe events in specific episodes.
        - Examples: "amusement park visit", "furo scene".
        - No weight system - treated as present/absent.
        3. **Character Tags**: Describe character attributes or tropes.
        - Examples: "glasses", "yandere", "school uniform".
        - No weight system - treated as present/absent.

        WEIGHT SYSTEM (Anime Tags Only):
        Anime tags use a star rating system to indicate relevance weight:
            +      : 0.5 stars (equivalent to 100 in numeric form)
            *      : 1 star    (equivalent to 200 in numeric form)
            *+     : 1.5 stars (equivalent to 300 in numeric form)
            **     : 2 stars   (equivalent to 400 in numeric form)
            **+    : 2.5 stars (equivalent to 500 in numeric form)
            ***    : 3 stars   (equivalent to 600 in numeric form)

        Note: Some anime tags are weightless (e.g., "male protagonist") and are treated as
            boolean flags. For these tags, weight constraints are ignored.

        Background: Internally, AniDB represents weights numerically (0, 100, 200, 300, 400,
        500, 600) corresponding to (0, 0.5, 1, 1.5, 2, 2.5, 3) stars respectively. While this
        method uses the star notation, other parts of the system may use the numeric format.

        SEARCH SYNTAX:
        - Basic inclusion/exclusion: Provide comma-separated tag names.
        Example: etags_include="pool episode, furo scene"

        - Weight constraints for anime tags: Use min()/max() operators.
        Format: "tag_name min(weight)", "tag_name max(weight)"
        Examples:
            "action max(*)"      : Action tag with ≤1 star (or absent)
            "nudity min(*+)"     : Nudity tag with ≥1.5 stars
            "nudity min(+), nudity max(*+)" : Nudity tag between 0.5-1.5 stars
            "male protagonist"   : Weightless tag (weight constraints ignored)

        Note: Multiple constraints for the same tag are allowed. For weightless tags,
        any specified weight constraints will be ignored during search.

        Args:
            atags_include: Anime tags to include (with optional weight constraints).
            atags_exclude: Anime tags to exclude (with optional weight constraints).
            etags_include: Episode tags to include (comma-separated).
            etags_exclude: Episode tags to exclude (comma-separated).
            ctags_include: Character tags to include (comma-separated).
            ctags_exclude: Character tags to exclude (comma-separated).
            order_by: Field to sort results by. Options:
                - "name": Title
                - "rating": AniDB rating
                - "average": Weighted average
                - "ucnt": User count
                - "airdate": Start date
                - "enddate": End date
            order_direction: Sort direction. Either "asc" (ascending) or "desc" (descending).
            limit: Maximum number of search results in response.

        Returns:
            List of search results matching the tag criteria

        Examples:
            >>> # Find anime with yandere characters without explicit nudity
            >>> search_by_tags(ctags_include="yandere", atags_exclude="nudity")

            >>> # Find high-action, low-tragedy anime
            >>> search_by_tags(atags_include="action min(**)", atags_exclude="tragedy max(*)")

            >>> # Find anime with male protagonist and school setting
            >>> search_by_tags(atags_include="male protagonist, school")

            >>> # Find anime with beach episodes, ordered by rating
            >>> search_by_tags(etags_include="beach episode", order_by="rating", order_direction="desc")
        """
        query_params = {
            "atags.include": atags_include,
            "atags.exclude": atags_exclude,
            "etags.include": etags_include,
            "etags.exclude": etags_exclude,
            "ctags.include": ctags_include,
            "ctags.exclude": ctags_exclude,
            f"orderby.{order_by}": f"0.{1 if order_direction == 'asc' else 2}",
            "do.update": "Search",
            "noalias": 1,
        }
        query_params = {k: v for k, v in query_params.items() if v != ""}
        query = urlencode(query_params, quote_via=quote)

        cache_key = "anidb-search-" + hashlib.sha256(json.dumps(query_params, sort_keys=True).encode()).hexdigest()[:16]
        text = await self._fetch_page(cache_key, f"/anime/?{query}")
        results = get_search_results(text)
        if limit:
            results = results[:limit]
        return results

    async def get_songs(self, anime_id: int) -> list[AniDBSong]:
        """Get songs list for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of songs for the anime
        """
        text = await self._fetch_page(f"anidb-{anime_id}", f"/anime/{anime_id}")
        return get_songs(text)
