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
        self,
        cache_dir: Optional[str] = None,
        max_rate: Optional[int] = None,
        time_period: Optional[int] = None,
        socks_url: Optional[str] = None,
        cookies_file: Optional[str] = None,
    ) -> None:
        """Initialize the AniDB scraper.

        Args:
            cache_dir: Directory to cache HTTP responses
            max_rate: Maximum number of requests per time period
            time_period: Time period in seconds for rate limiting
            socks_url: SOCKS proxy URL
            cookies_file: Path to cookies file for session persistence
        """
        settings = get_settings()
        if cache_dir is None:
            cache_dir = settings.cache_dir
        if max_rate is None:
            max_rate = settings.anidb_scraper_settings.rate_limit.max_rate
        if time_period is None:
            time_period = settings.anidb_scraper_settings.rate_limit.time_period
        if socks_url is None:
            socks_url = settings.anidb_scraper_settings.socks_url
        if cookies_file is None:
            cookies_file = settings.anidb_scraper_settings.cookies_file
        super().__init__(cache_dir, max_rate, time_period, "https://anidb.net", socks_url, cookies_file)

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

        Note: Access to adult (hentai) anime content requires authentication via AniDB cookies.
        Set the `cookies_file` configuration variable to the path of your cookies file
        to enable searching for adult-rated content.

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

        # don't cache search results, since they're unlikely to appear twice
        text = await self._http_client.get(f"/anime/?{query}", None)
        return get_search_results(text)
