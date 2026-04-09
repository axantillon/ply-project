from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional, Union

from .models import Movie
from .parser import parse_movie_json


@dataclass
class MovieCatalog:
    movies: list[Movie] = field(default_factory=list)

    def add(self, movie: Movie) -> None:
        self.movies.append(movie)

    def extend(self, movies: Iterable[Movie]) -> None:
        for movie in movies:
            self.add(movie)

    def get(self, tconst: str) -> Optional[Movie]:
        for movie in self.movies:
            if movie.tconst == tconst:
                return movie
        return None

    def __iter__(self) -> Iterator[Movie]:
        return iter(self.movies)

    def __len__(self) -> int:
        return len(self.movies)

    @classmethod
    def from_path(cls, path: Union[str, Path], skip_invalid: bool = False) -> "MovieCatalog":
        target = Path(path)
        catalog = cls()
        if target.is_dir():
            for child in sorted(target.iterdir()):
                if child.suffix.lower() == ".json":
                    catalog.extend(_load_json_file(child, skip_invalid=skip_invalid))
            return catalog
        if target.suffix.lower() == ".jsonl":
            catalog.extend(_load_jsonl_file(target, skip_invalid=skip_invalid))
            return catalog
        catalog.extend(_load_json_file(target, skip_invalid=skip_invalid))
        return catalog


def _load_json_file(path: Path, skip_invalid: bool = False) -> list[Movie]:
    text = path.read_text(encoding="utf-8")
    try:
        return [parse_movie_json(text)]
    except Exception:
        if skip_invalid:
            return []
        raise


def _load_jsonl_file(path: Path, skip_invalid: bool = False) -> list[Movie]:
    movies: list[Movie] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                movies.append(parse_movie_json(stripped))
            except Exception as exc:
                if skip_invalid:
                    continue
                raise ValueError(f"Failed to parse {path} line {line_number}: {exc}") from exc
    return movies
