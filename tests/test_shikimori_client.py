from typing import Any

import pytest

from anime_utils.clients.shikimori import ShikimoriAnime, ShikimoriClient


@pytest.mark.parametrize(
    "mal_id, info_subset",
    [
        (54722, {"name": "Mahou Shoujo ni Akogarete", "id": 54722, "kind": "tv"}),
        (1453, {"name": "Maison Ikkoku", "id": 1453, "kind": "tv"}),
        (10396, {"name": "Ben-To", "id": 10396, "kind": "tv"}),
    ],
)
@pytest.mark.asyncio
async def test_get_anime(mal_id: int, info_subset: dict[str, Any]):
    async with ShikimoriClient() as shikimori:
        anime = await shikimori.get_anime(mal_id)

    assert anime is not None
    for key in ShikimoriAnime.__annotations__:
        assert key in anime
    for key, value in info_subset.items():
        assert key in anime
        assert anime[key] == value


@pytest.mark.parametrize(
    "query, expected_name",
    [
        ("Mahou Shoujo ni Akogarete", "Mahou Shoujo ni Akogarete"),
        ("Maison Ikkoku", "Maison Ikkoku"),
        ("Ben-To", "Ben-To"),
    ],
)
@pytest.mark.asyncio
async def test_search(query: str, expected_name: str):
    async with ShikimoriClient() as shikimori:
        results = await shikimori.search(query, limit=1)

    assert len(results) > 0
    for anime in results:
        for key in ShikimoriAnime.__annotations__:
            assert key in anime
    assert results[0]["name"] == expected_name
