from __future__ import annotations

from pathlib import Path
from typing import Optional

from .catalog import MovieCatalog


DEFAULT_DATASET_CANDIDATES = (
    Path("data/processed/imdb_movies_full.jsonl"),
    Path("data/processed/imdb_movies_medium.jsonl"),
    Path("data/processed/imdb_movies_small.jsonl"),
)


def resolve_dataset(path: Optional[Path]) -> Path:
    if path is not None:
        return path
    for candidate in DEFAULT_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No default dataset found. Use --dataset to specify one explicitly.")


def load_catalog(path: Optional[Path]) -> MovieCatalog:
    return MovieCatalog.from_path(resolve_dataset(path), skip_invalid=True)
