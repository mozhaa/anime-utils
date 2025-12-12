from typing import Optional

import pytest

from anime_utils.sources.anidb.core import get_anime_tags
from anime_utils.sources.anidb.types import AniDBAnimeTag


@pytest.fixture
def tags_html() -> str:
    with open("tests/resources/anidb_tags.html", "r", encoding="utf-8") as f:
        return f.read()


def _find_tag(tags: list[AniDBAnimeTag], path: list[str]) -> AniDBAnimeTag:
    for name in path:
        for t in tags:
            if t["name"] == name:
                tags = t["children"]
                break
        else:
            pytest.fail(f"couldn't find tag with name {name}")
    return t


@pytest.mark.parametrize(
    "tag_hierarchy, id_, description_substring, weight, is_abstract, not_added",
    [
        (["fetishes", "breasts", "small breasts"], 2008, "flat chested", 200, False, False),
        (["setting", "place", "Earth", "Asia", "Japan", "Tokyo"], 2676, "Ogasawara", 300, False, False),
        (["elements", "pornography", "masturbation"], 2706, "orgasm", 200, False, False),
        (["elements", "sexual humour"], 7199, "ecchi", None, False, True),
        (["themes"], 2607, "tragic outcome", None, False, False),
        (["themes", "money"], 6243, "", None, True, False),
        (["dynamic", "cast", "strong female lead"], 4022, "distress", None, False, False),
    ],
)
def test_get_anime_tags(
    tags_html: str,
    tag_hierarchy: list[str],
    id_: int,
    description_substring: str,
    weight: Optional[int],
    is_abstract: bool,
    not_added: bool,
):
    anime_tags = get_anime_tags(tags_html)

    tag = _find_tag(anime_tags, tag_hierarchy)
    assert tag["id_"] == id_
    assert description_substring in tag["description"]
    assert tag["weight"] == weight
    assert tag["is_abstract"] == is_abstract
    assert tag["not_added"] == not_added
