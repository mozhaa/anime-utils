from pathlib import Path

from ..base import BaseClient
from .core import get_tags
from .types import AniDBTags


class AniDBScraper(BaseClient):
    """Client for scraping AniDB anime information."""

    def __init__(self, cache_dir: Path, max_rate: int = 1, time_period: int = 2) -> None:
        """Initialize the AniDB scraper.

        Args:
            cache_dir: Directory to cache HTTP responses
            max_rate: Maximum number of requests per time period
            time_period: Time period in seconds for rate limiting
        """
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
