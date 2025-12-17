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


class AniDBMainInfo(TypedDict):
    main_title: str
    type_: str
    year: str
    season: str
    main_tags: list[str]
    rating_value: Optional[float]
    rating_vote_count: Optional[int]
    average_value: Optional[float]
    average_vote_count: Optional[int]
    description: str


class AniDBCharacter(TypedDict):
    name: str
    id_: int
    is_main: bool
    general_info: str
    rating_value: float
    rating_vote_count: int
    main_tags: list[str]
    seiyuu: str


class AniDBSimilarAnime(TypedDict):
    name: str
    id_: int
    general_info: str
    approval_percentage: float
    approval_vote_count: int


class AniDBSearchResult(TypedDict):
    id_: int
    title: str
    type: str
    episodes: Optional[int]
    rating: Optional[float]
    rating_votes: Optional[int]
    average_rating: Optional[float]
    average_rating_votes: Optional[int]
    members: int
    aired_date: Optional[str]
    ended_date: Optional[str]


class AniDBSong(TypedDict):
    relation_type: str
    song_name: str
    song_id: int
    episode_range: str
    rating_value: Optional[float]
    rating_vote_count: int
    credit_type: str
    staff: str
