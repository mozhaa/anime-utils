from typing import Optional

import pytest

from anime_utils.sources.anidb.core import get_anime_tags, get_character_tags, get_episode_tags
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


@pytest.mark.parametrize(
    "name, id_, description_substring, episode_count, episode_list",
    [
        ("boobs in your face", 2815, "cleavage", 1, "12"),
        ("photo shoot", 6988, "fashion", 3, "3, 7-8"),
        ("pool episode", 6046, "beach", 2, "2, 7"),
    ],
)
def test_get_episode_tags(
    tags_html: str, name: str, id_: int, description_substring: str, episode_count: int, episode_list: str
):
    episode_tags = get_episode_tags(tags_html)

    for tag in episode_tags:
        if tag["name"] == name:
            assert description_substring in tag["description"]
            assert tag["episode_count"] == episode_count
            assert tag["episode_list"] == episode_list
            break
    else:
        pytest.fail("tag not found")


@pytest.mark.parametrize(
    "category, name, id_, character_count, size",
    [
        ("traits", "adolescent", 2224, 8, 10),
        ("clothing", "miniskirt", 2451, 3, 6),
        ("traits", "child", 2414, 1, 0),
        ("fetish appeals", "small breasts", 2008, 1, 1),
        ("looks", "black hair", 2241, 7, 9),
    ],
)
def test_get_character_tags(
    tags_html: str,
    category: str,
    name: str,
    id_: int,
    character_count: int,
    size: int,
):
    character_tags = get_character_tags(tags_html)

    for tag_category in character_tags:
        if tag_category["category"] == category:
            for tag in tag_category["tags"]:
                if tag["name"] == name:
                    assert tag["id_"] == id_
                    assert tag["character_count"] == character_count
                    assert tag["size"] == size
                    return
            pytest.fail("tag not found in category")
    pytest.fail("category not found")
