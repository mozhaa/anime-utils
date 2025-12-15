import logging
import pickle
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process

from .types import SearchResult

logger = logging.getLogger(__name__)


class AniDBXMLSearchEngine:
    def __init__(self, xml_path: str, pickle_path: Optional[str]) -> None:
        self.anime_list: list[tuple[str, str]] = []
        self.anime_titles: dict[str, list[str]] = {}

        if pickle_path is not None:
            try:
                logger.info(f"trying to load from pickle file {pickle_path}")
                with Path(pickle_path).expanduser().open("rb") as f:
                    self.anime_list, self.anime_titles = pickle.load(f)
                    return
            except FileNotFoundError:
                logger.info("pickle file does not exist yet")
            except Exception:
                logger.warning(f"failed to load data from pickle file {pickle_path}")

        logger.info(f"loading data from xml file {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for anime in root.findall("anime"):
            aid = anime.get("aid")
            titles: list[str] = []

            for title_elem in anime.findall("title"):
                lang = title_elem.get("{http://www.w3.org/XML/1998/namespace}lang")
                title_type = title_elem.get("type")

                if (lang in ["en", "x-jat"]) or (title_type == "main"):
                    title_text = title_elem.text
                    if title_text:
                        titles.append(title_text)

            if titles:
                combined = " ".join(titles).lower()
                self.anime_list.append((aid, combined))
                self.anime_titles[aid] = titles

        if pickle_path is not None:
            logger.info(f"saving data to pickle file {pickle_path}")
            path = Path(pickle_path).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as f:
                pickle.dump((self.anime_list, self.anime_titles), f)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        if not query:
            return []

        results = process.extract(
            query.lower(), [title for _, title in self.anime_list], scorer=fuzz.partial_ratio, limit=limit
        )

        return [
            SearchResult(score=score, anidb_id=aid, titles=self.anime_titles[aid])
            for title, score, idx in results
            for aid, _ in [self.anime_list[idx]]
        ]
