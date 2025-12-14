from typing import Literal, Optional
from urllib.parse import quote, urlencode

from anime_utils.config import get_settings

from ..base import BaseClient
from .core import get_characters, get_main_info, get_search_results, get_similar, get_tags
from .types import AniDBCharacter, AniDBMainInfo, AniDBSearchResult, AniDBSimilarAnime, AniDBTags


class AniDBScraper(BaseClient):
    """Client for scraping AniDB anime information."""

    name = "anidb"

    def __init__(
        self, cache_dir: Optional[str] = None, max_rate: Optional[int] = None, time_period: Optional[int] = None
    ) -> None:
        """Initialize the AniDB scraper.

        Args:
            cache_dir: Directory to cache HTTP responses
            max_rate: Maximum number of requests per time period
            time_period: Time period in seconds for rate limiting
        """
        settings = get_settings()
        if cache_dir is None:
            cache_dir = settings.cache_dir
        if max_rate is None:
            max_rate = settings.anidb_scraper_settings.rate_limit.max_rate
        if time_period is None:
            time_period = settings.anidb_scraper_settings.rate_limit.time_period
        super().__init__(cache_dir, max_rate, time_period, base_url="https://anidb.net")

    async def get_tags(self, anime_id: str) -> AniDBTags:
        """Get tags for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of tags for anime
        """
        text = await self._http_client.get(f"/anime/{anime_id}", f"anidb-{anime_id}")
        return get_tags(text)

    async def get_main_info(self, anime_id: str) -> AniDBMainInfo:
        """Get main information for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            Main information about the anime
        """
        text = await self._http_client.get(f"/anime/{anime_id}", f"anidb-{anime_id}")
        return get_main_info(text)

    async def get_characters(self, anime_id: str) -> list[AniDBCharacter]:
        """Get character information for an anime from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of characters in the anime
        """
        text = await self._http_client.get(f"/anime/{anime_id}", f"anidb-{anime_id}")
        return get_characters(text)

    async def get_similar(self, anime_id: str) -> list[AniDBSimilarAnime]:
        """Get similar anime recommendations from AniDB.

        Args:
            anime_id: The AniDB anime ID

        Returns:
            List of similar anime
        """
        text = await self._http_client.get(f"/anime/{anime_id}", f"anidb-{anime_id}")
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
    ) -> list[AniDBSearchResult]:
        """Search for anime by tags on AniDB.

        Args:
            atags_include: Anime tags to include in search
            atags_exclude: Anime tags to exclude from search
            etags_include: Episode tags to include in search
            etags_exclude: Episode tags to exclude from search
            ctags_include: Character tags to include in search
            ctags_exclude: Character tags to exclude from search
            order_by: Field to sort results by (name, rating, average, ucnt, airdate, enddate)
            order_direction: Sort direction (asc or desc)

        Returns:
            List of search results matching the tag criteria
        """
        query_params = {
            "atags_include": atags_include,
            "atags_exclude": atags_exclude,
            "etags_include": etags_include,
            "etags_exclude": etags_exclude,
            "ctags_include": ctags_include,
            "ctags_exclude": ctags_exclude,
            f"orderby.{order_by}": f"0.{1 if order_direction == 'asc' else 2}",
        }
        query = urlencode(query_params, quote_via=quote)

        # don't cache search results, since they're unlikely to appear twice
        text = await self._http_client.get(f"/anime/?{query}", None)
        return get_search_results(text)
