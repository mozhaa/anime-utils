from typing import Optional, TypedDict


class ShikimoriVideo(TypedDict):
    kind: str
    name: str
    url: str
    player_url: str


class ShikimoriExternalLink(TypedDict):
    kind: str
    url: str


class ShikimoriAnime(TypedDict):
    id: int
    name: str
    russian: str
    english: Optional[str]
    japanese: Optional[str]
    synonyms: list[str]
    kind: str
    rating: Optional[str]
    score: Optional[float]
    status: str
    episodes: Optional[int]
    duration: Optional[int]
    aired_on: Optional[str]
    released_on: Optional[str]
    url: str
    poster_original_url: str
    poster_main_url: str
    genres: list[str]
    videos: list[ShikimoriVideo]
    scores_stats: dict[int, int]
    statuses_stats: dict[str, int]
    external_links: list[ShikimoriExternalLink]
    anidb_id: Optional[int]
