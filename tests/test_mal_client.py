import pytest

from anime_utils import MALClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, results_subset",
    [
        ("mahou shoujo ni", {"anime": [54722], "manga": [120680]}),
        ("genshiken", {"anime": [240, 19889, 19159, 18465, 1813, 2508], "manga": [348]}),
        ("maison", {"anime": [1453], "manga": [688]}),
    ],
)
async def test_search(query: str, results_subset: dict[str, list[int]]):
    async with MALClient() as client:
        result = await client.search(query)

    for category, ids_subset in results_subset.items():
        assert category in result
        result_ids = set(item["id"] for item in result[category])
        for id_ in ids_subset:
            assert id_ in result_ids
