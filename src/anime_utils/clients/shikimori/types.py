from typing import Optional, TypedDict


class ShikimoriDate(TypedDict):
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]


class ShikimoriPoster(TypedDict):
    originalUrl: str
    mainUrl: str


class ShikimoriGenre(TypedDict):
    name: str


class ShikimoriVideo(TypedDict):
    kind: str
    name: str
    url: str
    playerUrl: str


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
    airedOn: ShikimoriDate
    releasedOn: ShikimoriDate
    url: str
    poster: ShikimoriPoster
    genres: list[ShikimoriGenre]
    videos: list[ShikimoriVideo]
    scoresStats: dict[str, int]
    statusesStats: dict[str, int]
    externalLinks: list[ShikimoriExternalLink]
    anidb_id: Optional[int]
