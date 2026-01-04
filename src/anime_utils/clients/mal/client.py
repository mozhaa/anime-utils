from typing import Self

from aiohttp import ClientSession

from anime_utils.clients.base import BaseClient
from anime_utils.clients.mal.types import MALItem
from anime_utils.http import default_headers


class MALClient(BaseClient):
    def __init__(self):
        self._session = ClientSession(headers=default_headers)

    async def __aenter__(self) -> Self:
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)

    async def search(self, query: str) -> dict[str, list[MALItem]]:
        from urllib.parse import quote_plus

        url = f"https://myanimelist.net/search/prefix.json?type=all&keyword={quote_plus(query)}&v=1"
        async with self._session.get(url) as response:
            data = await response.json()

        results: dict[str, list[MALItem]] = {}
        for category in data["categories"]:
            results[category["type"]] = category["items"]

        return results
