import itertools
import re
from typing import Optional

import parsel

from anime_utils.clients.anidb.types import (
    AniDBAnimeTag,
    AniDBCharacter,
    AniDBCharacterTag,
    AniDBCharacterTagCategory,
    AniDBEpisodeTag,
    AniDBMainInfo,
    AniDBSearchResult,
    AniDBSimilarAnime,
    AniDBTags,
)


def get_anime_tags(text: str) -> list[AniDBAnimeTag]:
    selector = parsel.Selector(text=text)

    anime_tags: list[AniDBAnimeTag] = []
    for tag_element in selector.css(".animetags .tag"):
        if tag_element.css("::attr(id)").get() == "eptb_0":
            # episode specific tags
            break

        name = tag_element.css(".tagname::text").get()
        if name is None:
            raise RuntimeError(f"tag has no name: {tag_element.get()}")

        href = tag_element.css("a::attr(href)").get()
        if href is None:
            raise RuntimeError(f"href not found inside tag: {tag_element.get()}")
        m = re.match("/tag/(\\d+)/.*", href)
        if m is None:
            raise RuntimeError(f"failed to get tag id from href: {href}")
        id_ = int(m.group(1))

        description = tag_element.css(".g_bubble.text::text").get()
        if description is None:
            raise RuntimeError(f"no description inside tag: {tag_element.get()}")

        weight = tag_element.css("::attr(data-anidb-weight)").get()
        if weight == "" or weight == "0":
            # weightless tags
            weight = None
        elif weight is not None:
            weight = int(weight)

        not_added = tag_element.css(".not_added").get() is not None

        is_abstract = "abstract" in tag_element.css("::attr(class)").get("")

        tag = AniDBAnimeTag(
            name=name,
            id_=id_,
            description=description,
            weight=weight,
            is_abstract=is_abstract,
            not_added=not_added,
            children=[],
        )

        # find parent tag using indent value
        indent = tag_element.css(".indent::text").get("").count("·")
        list_to_add = anime_tags
        for _ in range(indent):
            if len(list_to_add) == 0:
                raise RuntimeError(f"too big indent for tag: {indent}")
            list_to_add = list_to_add[-1]["children"]

        list_to_add.append(tag)

    return anime_tags


def get_episode_tags(text: str) -> list[AniDBEpisodeTag]:
    selector = parsel.Selector(text=text)

    episode_tags: list[AniDBEpisodeTag] = []

    for tag_element in selector.css(".animetags .tag[data-anidb-groupid='eptb_0']"):
        name = tag_element.css(".tagname::text").get()
        if name is None:
            raise RuntimeError(f"tag has no name: {tag_element.get()}")

        href = tag_element.css("a::attr(href)").get()
        if href is None:
            raise RuntimeError(f"href not found inside tag: {tag_element.get()}")
        m = re.match("/tag/(\\d+)/.*", href)
        if m is None:
            raise RuntimeError(f"failed to get tag id from href: {href}")
        id_ = int(m.group(1))

        description = tag_element.css(".g_bubble.text::text").get()
        if description is None:
            raise RuntimeError(f"no description inside tag: {tag_element.get()}")

        weight_text = tag_element.css(".weight.cnt::text").get()
        if weight_text is None:
            raise RuntimeError(f"no episode count inside tag: {tag_element.get()}")

        episode_count_match = re.match(r"(\d+)\s+eps", weight_text.strip())
        if episode_count_match is None:
            raise RuntimeError(f"failed to parse episode count from: {weight_text}")
        episode_count = int(episode_count_match.group(1))

        episode_list_text = tag_element.css(".weight.cnt .text::text").get()
        if episode_list_text is None:
            raise RuntimeError(f"no episode list inside tag: {tag_element.get()}")

        episode_list_match = re.search(r"applies to episode\(s\):\s*(.+)", episode_list_text.strip())
        if episode_list_match is None:
            raise RuntimeError(f"failed to parse episode list from: {episode_list_text}")
        episode_list = episode_list_match.group(1).strip()

        tag = AniDBEpisodeTag(
            name=name,
            id_=id_,
            description=description,
            episode_count=episode_count,
            episode_list=episode_list,
        )

        episode_tags.append(tag)

    return episode_tags


def get_character_tags(text: str) -> list[AniDBCharacterTagCategory]:
    selector = parsel.Selector(text=text)

    categories: list[AniDBCharacterTagCategory] = []

    for category_element in selector.css("#chartags > div[class]"):
        category_name = category_element.css("h3 .tagname::text").get("").strip()
        if category_name == "":
            continue

        tags: list[AniDBCharacterTag] = []
        for tag_element in category_element.css(".tag"):
            name = tag_element.css(".tagname::text").get("").strip()
            if name == "":
                raise RuntimeError(f"tag has no name: {tag_element.get()}")
            if "--" in name:
                name = name.split("--")[0].strip()

            count = tag_element.css(".tagname .cnt::text").get("")
            m = re.match(r"\((\d+)\)", count.strip())
            if m is None:
                raise RuntimeError(f"failed to get count from cnt: {count}")
            count = int(m.group(1))

            href = tag_element.css("a::attr(href)").get()
            if href is None:
                raise RuntimeError(f"href not found inside tag: {tag_element.get()}")
            m = re.search(r"/tag/(\d+)/", href)
            if m is None:
                raise RuntimeError(f"failed to get tag id from href: {href}")
            id_ = int(m.group(1))

            description = tag_element.css(".g_bubble.text::text").get()
            if description is None:
                raise RuntimeError(f"no description inside tag: {tag_element.get()}")

            class_attr = tag_element.css("::attr(class)").get()
            if class_attr is None:
                raise RuntimeError(f"tag element has no size* class: {class_attr}")
            m = re.search(r"size(\d+)", class_attr)
            if m is None:
                raise RuntimeError(f"failed to get size from size* class: {class_attr}")
            size = int(m.group(1))

            tags.append(
                AniDBCharacterTag(name=name, id_=id_, description=description, character_count=count, size=size)
            )

        categories.append(AniDBCharacterTagCategory(category=category_name, tags=tags))

    return categories


def get_tags(text: str) -> AniDBTags:
    return AniDBTags(
        anime_tags=get_anime_tags(text),
        episode_tags=get_episode_tags(text),
        character_tags=get_character_tags(text),
    )


def _safe_float(s: str) -> Optional[float]:
    try:
        return float(s.strip())
    except ValueError:
        return None


def _safe_int(s: str) -> Optional[int]:
    try:
        return int(s.strip())
    except ValueError:
        return None


def get_main_info(text: str) -> AniDBMainInfo:
    selector = parsel.Selector(text=text)

    main_title = selector.css("#tab_1_pane [itemprop='name']::text").get("").strip()
    if main_title == "":
        raise RuntimeError("main title not found")

    type_ = "".join(selector.css("#tab_1_pane tr.type .value *::text").getall()).strip()
    if type_ == "":
        raise RuntimeError("type not found")

    year = "".join(selector.css("#tab_1_pane tr.year .value *::text").getall()).strip()
    if year == "":
        raise RuntimeError("year not found")

    season = "".join(selector.css("#tab_1_pane tr.season .value *::text").getall()).strip()
    if season == "":
        raise RuntimeError("season not found")

    main_tags_elements = selector.css("#tab_1_pane tr.tags [itemprop='genre']")
    main_tags = []
    for tag_element in main_tags_elements:
        tag_text = tag_element.css("::text").get()
        if tag_text:
            main_tags.append(tag_text.strip())

    rating_value = _safe_float(selector.css("#tab_1_pane tr.rating [itemprop='ratingValue']::text").get(""))
    rating_vote_count = _safe_int(selector.css("#tab_1_pane tr.rating [itemprop='ratingCount']::text").get("")[1:-1])
    average_value = _safe_float(selector.css("#tab_1_pane tr.tmprating .value::text").get(""))
    average_vote_count = _safe_int(selector.css("#tab_1_pane tr.tmprating .count::text").get("")[1:-1])

    description = "".join(selector.css(".g_section.desc *::text").getall())
    if description is None:
        raise RuntimeError("description not found")
    description = description.strip()

    return AniDBMainInfo(
        main_title=main_title,
        type_=type_,
        year=year,
        season=season,
        main_tags=main_tags,
        rating_value=rating_value,
        rating_vote_count=rating_vote_count,
        average_value=average_value,
        average_vote_count=average_vote_count,
        description=description,
    )


def get_characters(text: str) -> list[AniDBCharacter]:
    selector = parsel.Selector(text=text)

    characters: list[AniDBCharacter] = []

    character_selector = '#characterlist .{} [id^="charid_"]'
    main_chars = selector.css(character_selector.format("main"))
    secondary_chars = selector.css(character_selector.format("secondary"))
    chars_iter = itertools.chain(
        zip(main_chars, itertools.repeat(True)),
        zip(secondary_chars, itertools.repeat(False)),
    )

    for character_element, is_main in chars_iter:
        id_attr = character_element.css("::attr(id)").get()
        if id_attr is None:
            raise RuntimeError(f"character element has no id: {character_element.get()}")

        m = re.match(r"(?:charid_|crtid_)(\d+)", id_attr)
        if m is None:
            raise RuntimeError(f"failed to get character id from id: {id_attr}")
        id_ = int(m.group(1))

        name = character_element.css(".data > .name [itemprop='name']::text").get("").strip()
        if name == "":
            raise RuntimeError(f"character has no name: {character_element.get()}")

        general_info = character_element.css(".general::text").get("").strip(" \n,")

        rating_value_text = character_element.css(".rating .value::text").get()
        if rating_value_text is None:
            rating_value = 0.0
        else:
            rating_value = float(rating_value_text.strip())

        rating_vote_count_text = character_element.css(".rating .count::text").get()
        if rating_vote_count_text is None:
            rating_vote_count = 0
        else:
            rating_vote_count = int(rating_vote_count_text.strip("()"))

        main_tags = []
        for tag_element in character_element.css(".general .g_tag .tagname"):
            main_tags.append(tag_element.css("::text").get("").strip())

        seiyuu_element = character_element.css(".seiyuu [itemprop='name']").get()
        if seiyuu_element is None:
            seiyuu = ""
        else:
            seiyuu = "".join(character_element.css(".seiyuu [itemprop='name']::text").getall()).strip()

        characters.append(
            AniDBCharacter(
                name=name,
                id_=id_,
                is_main=is_main,
                general_info=general_info,
                rating_value=rating_value,
                rating_vote_count=rating_vote_count,
                main_tags=main_tags,
                seiyuu=seiyuu,
            )
        )

    return characters


def get_similar(text: str) -> list[AniDBSimilarAnime]:
    selector = parsel.Selector(text=text)

    similar_animes: list[AniDBSimilarAnime] = []

    for anime_element in selector.css("#similaranime .approved"):
        name = anime_element.css(".name a::text").get("").strip()
        if name == "":
            raise RuntimeError(f"similar anime has no name: {anime_element.get()}")

        href = anime_element.css(".name a::attr(href)").get()
        if href is None:
            raise RuntimeError(f"similar anime has no href: {anime_element.get()}")
        m = re.match(r"/anime/(\d+)", href)
        if m is None:
            raise RuntimeError(f"failed to get anime id from href: {href}")
        id_ = int(m.group(1))

        general_info = anime_element.css(".info .series::text").get("").strip()
        if general_info == "":
            raise RuntimeError(f"similar anime has no general info: {anime_element.get()}")

        approval_text = anime_element.css(".approval::text").get()
        if approval_text is None:
            raise RuntimeError(f"similar anime has no approval text: {anime_element.get()}")

        approval_match = re.search(r"(\d+\.\d+)%\s*\((\d+)\s+votes\)", approval_text.strip())
        if approval_match is None:
            raise RuntimeError(f"failed to parse approval from: {approval_text}")
        approval_percentage = float(approval_match.group(1))
        approval_vote_count = int(approval_match.group(2))

        similar_animes.append(
            AniDBSimilarAnime(
                name=name,
                id_=id_,
                general_info=general_info,
                approval_percentage=approval_percentage,
                approval_vote_count=approval_vote_count,
            )
        )

    return similar_animes


def _parse_rating_and_votes(text: str) -> tuple[Optional[float], Optional[int]]:
    if not text:
        return None, None

    m = re.search(r"\((\d+)\)", text)
    if m is None:
        votes = None
    else:
        votes = int(m.group(1))

    if "N/A" in text:
        rating = None
    else:
        rating = float(text.split(" ")[0])

    return rating, votes


def get_search_results(text: str) -> list[AniDBSearchResult]:
    selector = parsel.Selector(text=text)

    results: list[AniDBSearchResult] = []

    for element in selector.css('#animelist > tbody > tr[id^="a"]'):
        id_ = element.css("::attr(id)").get("")
        m = re.match(r"a(\d+)", id_)
        if m is None:
            raise RuntimeError(f"failed to parse id from {id_}")
        id_ = int(m.group(1))

        title = element.css('td[data-label="Title"] a::text').get("").strip()
        if not title:
            raise RuntimeError(f"Anime with id {id_} has no title.")

        type_ = element.css('td[data-label="Type"]::text').get()
        if type_ is None:
            raise RuntimeError(f"failed to get type from {element.get()}")
        type_ = type_.strip()

        episodes_text = "".join(element.css('td[data-label="Eps"] *::text').getall())
        if episodes_text == "":
            raise RuntimeError(f"failed to get episodes from {element.get()}")
        episodes = _safe_int(episodes_text)

        members = element.css('td[data-label="User"]::text').get()
        if members is None:
            raise RuntimeError(f"failed to get user count from {element.get()}")
        members = int(members.strip())

        aired_date = element.css('td[data-label="Aired"]::text').get()
        if aired_date is None:
            raise RuntimeError(f"failed to get aired date from {element.get()}")
        aired_date = aired_date.strip()

        ended_date = element.css('td[data-label="Ended"]::text').get()
        if ended_date is None:
            raise RuntimeError(f"failed to get ended date from {element.get()}")
        ended_date = ended_date.strip()

        rating_text = element.css('td[data-label="Rating"]::text').get("").strip()
        rating, rating_votes = _parse_rating_and_votes(rating_text)

        average_rating_text = element.css('td[data-label="Average"]::text').get("").strip()
        average_rating, average_rating_votes = _parse_rating_and_votes(average_rating_text)

        results.append(
            AniDBSearchResult(
                id_=id_,
                title=title,
                type=type_,
                episodes=episodes,
                rating=rating,
                rating_votes=rating_votes,
                average_rating=average_rating,
                average_rating_votes=average_rating_votes,
                members=members,
                aired_date=aired_date,
                ended_date=ended_date,
            )
        )

    return results
