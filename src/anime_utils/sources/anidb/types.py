from typing import Optional, TypedDict


class AniDBAnimeTag(TypedDict):
    name: str
    id_: int
    description: str
    weight: Optional[int]
    is_abstract: bool
    not_added: bool
    children: list["AniDBAnimeTag"]


class AniDBEpisodeTag(TypedDict):
    name: str
    id_: int
    description: str
    episode_count: int
    episode_list: str


class AniDBCharacterTag(TypedDict):
    name: str
    id_: int
    description: str
    character_count: int
    size: int


class AniDBCharacterTagCategory(TypedDict):
    category: str
    tags: list[AniDBCharacterTag]


class AniDBTags(TypedDict):
    anime_tags: list[AniDBAnimeTag]
    episode_tags: list[AniDBEpisodeTag]
    character_tags: list[AniDBCharacterTagCategory]
