from typing import Optional

import pytest

from anime_utils.sources.anidb.core import (
    get_anime_tags,
    get_character_tags,
    get_characters,
    get_episode_tags,
    get_main_info,
    get_similar,
)
from anime_utils.sources.anidb.types import AniDBAnimeTag, AniDBCharacter


@pytest.fixture
def page_html() -> str:
    with open("tests/resources/anidb_7286.html", "r", encoding="utf-8") as f:
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
    page_html: str,
    tag_hierarchy: list[str],
    id_: int,
    description_substring: str,
    weight: Optional[int],
    is_abstract: bool,
    not_added: bool,
):
    anime_tags = get_anime_tags(page_html)

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
    page_html: str, name: str, id_: int, description_substring: str, episode_count: int, episode_list: str
):
    episode_tags = get_episode_tags(page_html)

    for tag in episode_tags:
        if tag["name"] == name:
            assert description_substring in tag["description"]
            assert tag["episode_count"] == episode_count
            assert tag["episode_list"] == episode_list
            break
    else:
        pytest.fail("tag not found")


@pytest.mark.parametrize(
    "category, name, id_, description_substring, character_count, size",
    [
        ("traits", "adolescent", 2224, "13 to 19", 8, 10),
        ("clothing", "miniskirt", 2451, "hemline", 3, 6),
        ("traits", "child", 2414, "3 to 12", 1, 0),
        ("fetish appeals", "small breasts", 2008, "flat chested", 1, 1),
        ("looks", "black hair", 2241, "black hair", 7, 9),
        ("looks", "handsome", 290, "", 1, 1),
        ("traits", "timid", 1465, "shy", 1, 2),
    ],
)
def test_get_character_tags(
    page_html: str,
    category: str,
    name: str,
    id_: int,
    description_substring: str,
    character_count: int,
    size: int,
):
    character_tags = get_character_tags(page_html)

    for tag_category in character_tags:
        if tag_category["category"] == category:
            for tag in tag_category["tags"]:
                if tag["name"] == name:
                    assert tag["id_"] == id_
                    assert description_substring in tag["description"]
                    assert tag["character_count"] == character_count
                    assert tag["size"] == size
                    return
            pytest.fail("tag not found in category")
    pytest.fail("category not found")


def test_get_main_info(page_html: str):
    info = get_main_info(page_html)

    assert info["main_title"] == "B Gata H Kei"
    assert info["type_"] == "TV Series, 12 episodes"
    assert info["year"] == "02.04.2010 until 18.06.2010"
    assert info["season"] == "Spring 2010"
    assert info["main_tags"] == [
        "4-koma manga",
        "comedy",
        "coming of age",
        "ecchi",
        "love polygon",
        "manga",
        "seinen",
        "the arts",
    ]
    assert info["rating_value"] == 5.24
    assert info["rating_vote_count"] == 4912
    assert info["average_value"] == 6.93
    assert info["average_vote_count"] == 4957
    assert "manga by Sanri Youko" in info["description"]
    assert "sexually inexperienced schoolgirl" in info["description"]
    assert "her seduction attempts begin..." in info["description"]


def _find_character(characters: list[AniDBCharacter], id_: int) -> AniDBCharacter:
    for character in characters:
        if character["id_"] == id_:
            return character
    pytest.fail(f"character with id {id_} was not found")


@pytest.mark.parametrize(
    "name, id_, is_main, general_info, rating_value, rating_vote_count, tags_sublist, seiyuu",
    [
        (
            "Katase Aoi",
            15171,
            False,
            "female",
            4.92,
            22,
            ["adolescent", "miniskirt", "student", "tsukkomi"],
            "Kitta Izumi",
        ),
        (
            "Yamada",
            13815,
            True,
            "female",
            6.49,
            83,
            ["green eyes", "perverted", "long hair"],
            "Tamura Yukari",
        ),
    ],
)
def test_get_characters(
    page_html: str,
    name: str,
    id_: int,
    is_main: bool,
    general_info: str,
    rating_value: float,
    rating_vote_count: int,
    tags_sublist: list[str],
    seiyuu: str,
):
    characters = get_characters(page_html)

    character = _find_character(characters, id_)
    assert character["name"] == name
    assert character["is_main"] == is_main
    assert character["general_info"] == general_info
    assert character["rating_value"] == rating_value
    assert character["rating_vote_count"] == rating_vote_count
    for tag in tags_sublist:
        assert tag in character["main_tags"]
    assert character["seiyuu"] == seiyuu


@pytest.mark.parametrize(
    "name, id_, general_info, approval_percentage, approval_vote_count",
    [
        ("Hajimete no Gal", 12554, "TV Series, 2017, 10 eps,", 88.24, 17),
        ("Midara na Ao-chan wa Benkyou ga Dekinai", 14519, "TV Series, 2019, 12 eps,", 84.62, 13),
        ("Joshikousei: Girl`s High", 4067, "TV Series, 2006, 12 eps,", 83.33, 12),
        ("Onii-chan no Koto Nanka Zenzen Suki ja Naindakara ne!!", 7978, "TV Series, 2011, 12 eps,", 53.45, 58),
    ],
)
def test_get_similar(
    page_html: str, name: str, id_: int, general_info: str, approval_percentage: float, approval_vote_count: int
):
    similar_anime = get_similar(page_html)

    assert len(similar_anime) == 4

    for anime in similar_anime:
        if anime["name"] == name:
            assert anime["id_"] == id_
            assert anime["general_info"] == general_info
            assert anime["approval_percentage"] == approval_percentage
            assert anime["approval_vote_count"] == approval_vote_count
            return
    pytest.fail(f"similar anime with name {name} was not found")
