import re

import parsel

from .types import AniDBAnimeTag, AniDBCharacterTagCategory, AniDBEpisodeTag, AniDBTags


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
        indent = (tag_element.css(".indent::text").get() or "").count("·")
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

    for tag_element in selector.css(".tag[data-anidb-groupid='eptb_0']"):
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
    pass


def get_tags(text: str) -> AniDBTags:
    return AniDBTags(
        anime_tags=get_anime_tags(text),
        episode_tags=get_episode_tags(text),
        character_tags=get_character_tags(text),
    )
