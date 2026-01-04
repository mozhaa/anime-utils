import json
from typing import Optional
from urllib.parse import quote_plus

from anime_utils.clients.base import HTTPClient
from anime_utils.clients.mal.types import MALItem
from anime_utils.config import get_settings


class MALClient(HTTPClient):
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
    ):
        super().__init__(
            get_settings().mal_client_settings,
            max_rate,
            time_period,
            max_attempts,
            backoff_factor,
            initial_delay,
            base_url,
            socks_url,
            cookies_file,
        )

    async def search(self, query: str) -> dict[str, list[MALItem]]:
        url = f"https://myanimelist.net/search/prefix.json?type=all&keyword={quote_plus(query)}&v=1"

        async for attempt in self._retry:
            with attempt:
                async with self._limiter:
                    async with self._session.get(url) as response:
                        response.raise_for_status()
                        text = await response.text()

        data = json.loads(text)
        results: dict[str, list[MALItem]] = {}
        for category in data["categories"]:
            results[category["type"]] = category["items"]

        return results
