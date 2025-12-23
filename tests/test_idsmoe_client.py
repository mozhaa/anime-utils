from typing import Any

import pytest

from anime_utils.clients.idsmoe import IDsMoeClient


@pytest.mark.parametrize(
    "id_, platform, info_subset",
    [
        (17910, "anidb", {"title": "Mahou Shoujo ni Akogarete", "anilist": 162780, "myanimelist": 54722}),
        (1453, "anilist", {"title": "Maison Ikkoku", "myanimelist": 1453, "anilist": 1453, "anidb": 288}),
        (10396, "shikimori", {"title": "Ben-To", "myanimelist": 10396, "anilist": 10396, "anidb": 8292}),
    ],
)
@pytest.mark.asyncio
async def test_get(id_: int, platform: str, info_subset: dict[str, Any]):
    async with IDsMoeClient() as idsmoe:
        info = await idsmoe.get(id_, platform)

    assert info is not None
    for key, value in info_subset.items():
        assert key in info
        assert info[key] == value
