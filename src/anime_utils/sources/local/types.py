from typing import TypedDict


class SearchResult(TypedDict):
    score: float
    anidb_id: int
    titles: list[str]
