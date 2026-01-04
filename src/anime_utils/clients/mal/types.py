from typing import TypedDict


class MALPayload(TypedDict):
    media_type: str
    start_year: int
    aired: str
    score: str
    status: str


class MALItem(TypedDict):
    id: int
    type: str
    name: str
    url: str
    image_url: str
    thumbnail_url: str
    payload: MALPayload
    es_score: float
