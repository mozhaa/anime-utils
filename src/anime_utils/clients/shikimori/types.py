from typing import Optional, TypedDict


class ShikimoriDate(TypedDict):
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]


class ShikimoriPoster(TypedDict):
    original_url: str
    main_url: str


class ShikimoriGenre(TypedDict):
    name: str


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
    aired_on: ShikimoriDate
    released_on: ShikimoriDate
    url: str
    poster: ShikimoriPoster
    genres: list[ShikimoriGenre]
    videos: list[ShikimoriVideo]
    scores_stats: dict[int, int]
    statuses_stats: dict[str, int]
    external_links: list[ShikimoriExternalLink]
    anidb_id: Optional[int]
