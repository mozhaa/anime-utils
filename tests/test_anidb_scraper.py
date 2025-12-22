from typing import Optional

import pytest

from anime_utils.clients.anidb.core import (
    get_anime_tags,
    get_character_tags,
    get_characters,
    get_episode_tags,
    get_main_info,
    get_search_results,
    get_similar,
    get_songs,
)
from anime_utils.clients.anidb.types import AniDBAnimeTag, AniDBCharacter, AniDBSong


@pytest.fixture
def anidb_7286_html() -> str:
    with open("tests/resources/anidb_7286.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def anidb_17910_html() -> str:
    with open("tests/resources/anidb_17910.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def search_results_html() -> str:
    with open("tests/resources/search_results.html", "r", encoding="utf-8") as f:
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
    anidb_7286_html: str,
    tag_hierarchy: list[str],
    id_: int,
    description_substring: str,
    weight: Optional[int],
    is_abstract: bool,
    not_added: bool,
):
    anime_tags = get_anime_tags(anidb_7286_html)

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
    anidb_7286_html: str, name: str, id_: int, description_substring: str, episode_count: int, episode_list: str
):
    episode_tags = get_episode_tags(anidb_7286_html)

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
    anidb_7286_html: str,
    category: str,
    name: str,
    id_: int,
    description_substring: str,
    character_count: int,
    size: int,
):
    character_tags = get_character_tags(anidb_7286_html)

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


def test_get_main_info(anidb_7286_html: str):
    info = get_main_info(anidb_7286_html)

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
    anidb_7286_html: str,
    name: str,
    id_: int,
    is_main: bool,
    general_info: str,
    rating_value: float,
    rating_vote_count: int,
    tags_sublist: list[str],
    seiyuu: str,
):
    characters = get_characters(anidb_7286_html)

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
    anidb_7286_html: str, name: str, id_: int, general_info: str, approval_percentage: float, approval_vote_count: int
):
    similar_anime = get_similar(anidb_7286_html)

    assert len(similar_anime) == 4

    for anime in similar_anime:
        if anime["name"] == name:
            assert anime["id_"] == id_
            assert anime["general_info"] == general_info
            assert anime["approval_percentage"] == approval_percentage
            assert anime["approval_vote_count"] == approval_vote_count
            return
    pytest.fail(f"similar anime with name {name} was not found")


@pytest.mark.parametrize(
    "id_, title, type_, episodes, rating, rating_votes, average_rating, "
    "average_rating_votes, members, aired_date, ended_date",
    [
        (24, ".hack//Sign", "TV Series", 26, 5.18, 7061, 7.11, 7201, 13921, "04.04.2002", "26.09.2002"),
        (12876, "?", "Movie", 1, 2.21, 197, 4.18, 202, 365, "??.??.1932", "??.??.1932"),
        (
            19310,
            '"Omae Gotoki ga Maou ni Kateru to Omou na" to Yuusha Party o Tsuihou Sareta node, '
            "Outo de Kimama ni Kurashitai",
            "TV Series",
            None,
            None,
            0,
            None,
            0,
            0,
            "09.01.2026",
            "-",
        ),
        (
            3689,
            '"Aesop" no Ohanashi yori: Ushi to Kaeru, Yokubatta Inu',
            "Movie",
            1,
            None,
            6,
            None,
            7,
            62,
            "21.03.1970",
            "21.03.1970",
        ),
        (10143, '"0"', "Music Video", 1, 2.86, 240, 4.44, 242, 468, "23.10.2013", "23.10.2013"),
        (
            17129,
            '"Anata o Hitokoto de Arawashite Kudasai" no Shitsumon ga Nigate da.',
            "Web",
            1,
            5.55,
            47,
            5.77,
            48,
            118,
            "12.01.2022",
            "12.01.2022",
        ),
        (
            17754,
            "#Compass 2.0: Sentou Setsuri Kaiseki System",
            "TV Series",
            12,
            1.90,
            42,
            4.32,
            44,
            366,
            "08.04.2025",
            "24.06.2025",
        ),
        (18901, '"Oshi no Ko" (2026)', "TV Series", None, None, 0, None, 0, 6, "14.01.2026", "-"),
        (5391, ".hack//G.U. Returner", "OVA", 1, 3.98, 828, 6.20, 843, 2883, "??.07.2007", "??.07.2007"),
        (
            12936,
            '"Eikou Naki Tensai-tachi" kara no Monogatari',
            "TV Special",
            2,
            None,
            5,
            None,
            7,
            54,
            "25.03.2017",
            "28.05.2017",
        ),
    ],
)
def test_get_search_results(
    search_results_html: str,
    id_: int,
    title: str,
    type_: str,
    episodes: Optional[int],
    rating: Optional[float],
    rating_votes: Optional[int],
    average_rating: Optional[float],
    average_rating_votes: Optional[int],
    members: int,
    aired_date: str,
    ended_date: str,
):
    results = get_search_results(search_results_html)

    assert len(results) == 30

    for result in results:
        if result["id_"] == id_:
            assert result["title"] == title
            assert result["type"] == type_
            assert result["episodes"] == episodes
            assert result["rating"] == rating
            assert result["rating_votes"] == rating_votes
            assert result["average_rating"] == average_rating
            assert result["average_rating_votes"] == average_rating_votes
            assert result["members"] == members
            assert result["aired_date"] == aired_date
            assert result["ended_date"] == ended_date
            return
    pytest.fail(f"search result with id {id_} was not found")


def _find_song(songs: list[AniDBSong], category: str, number: int) -> AniDBSong:
    for song in songs:
        if song["category"] == category and song["number"] == number:
            return song
    pytest.fail(f"song '{category}' #{number} was not found")


@pytest.mark.parametrize(
    "category, number, song_name, song_id, episode_range, rating_value, rating_vote_count, staff_subset",
    [
        (
            "opening",
            1,
            "My Dream Girls",
            110129,
            "1-13, OP1",
            None,
            2,
            {"Vocals/Performed by (歌)": "Nacherry", "Lyrics (作詞)": "Motokiyo"},
        ),
        (
            "ending",
            1,
            "Togetoge Sadistic",
            110201,
            "1-9, ED1",
            None,
            1,
            {"Vocals/Performed by (歌)": "Izumi Fuuka, Koga Aoi, Sugiura Shiori", "Lyrics (作詞)": "Karasuya Sabou"},
        ),
        (
            "ending",
            2,
            "Togetoge Sadistic",
            111187,
            "10-13, ED2",
            None,
            0,
            {"Vocals/Performed by (歌)": "Aisaka Yuuka, Izumi Fuuka, Koga Aoi, Sugiura Shiori, Tsuda Minami"},
        ),
        (
            "insert song",
            1,
            "Lovely Loco",
            111234,
            "8-9",
            None,
            0,
            {"Vocals/Performed by (歌)": "Aisaka Yuuka"},
        ),
        (
            "insert song",
            2,
            "My Dream Girls",
            110129,
            "13",
            None,
            2,
            {"Music Composition (作曲)": "Motokiyo"},
        ),
    ],
)
def test_get_songs(
    anidb_17910_html: str,
    category: str,
    number: int,
    song_name: str,
    song_id: int,
    episode_range: str,
    rating_value: Optional[float],
    rating_vote_count: int,
    staff_subset: dict[str, str],
):
    songs = get_songs(anidb_17910_html)
    print(songs)

    song = _find_song(songs, category, number)
    assert song["category"] == category
    assert song["number"] == number
    assert song["song_name"] == song_name
    assert song["song_id"] == song_id
    assert song["episode_range"] == episode_range
    assert song["rating_value"] == rating_value
    assert song["rating_vote_count"] == rating_vote_count
    for credit_type, creator in staff_subset.items():
        assert credit_type in song["staff"]
        assert song["staff"][credit_type] == creator
