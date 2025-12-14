from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    cache_dir: Path


_config: Optional[Config] = None


def configure(cache_dir: Path | str) -> None:
    global _config

    if isinstance(cache_dir, str):
        cache_dir = Path(cache_dir)

    cache_dir.mkdir(parents=True, exist_ok=True)
    _config = Config(cache_dir=cache_dir)


def get_config() -> Config:
    if _config is None:
        raise RuntimeError("Configuration not set. Call configure() first.")
    return _config
