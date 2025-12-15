from typing import Optional

from anime_utils.config import get_settings

from ..base import BaseClient
from .anidb_xml import AniDBXMLSearchEngine
from .types import SearchResult


class LocalClient(BaseClient):
    """Client for extracting data from local data sources."""

    name = "local"

    def __init__(self, xml_path: Optional[str] = None, pickle_path: Optional[str] = None) -> None:
        """Initialize the Local Client.

        Args:
            xml_path: Path to XML, obtained from https://wiki.anidb.net/API
            pickle_path: Optional path to load/save parsed data for faster loading
        """
        if xml_path is None:
            xml_path = get_settings().local_settings.xml_path
            if xml_path is None:
                raise RuntimeError("xml_path is not provided in config (required for LocalClient)")
        if pickle_path is None:
            pickle_path = get_settings().local_settings.pickle_path
        self._engine = AniDBXMLSearchEngine(xml_path, pickle_path)

    async def search_by_title(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search anime by title (fuzzy matching with scores).

        Args:
            query: Query to search for
            limit: Maximum amount of elements in response

        Returns:
            List of search results (each includes score, anidb_id and list of titles).
        """
        return self._engine.search(query, limit=limit)
