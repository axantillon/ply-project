from __future__ import annotations

from typing import Optional

from .models import Movie


def search_movies(
    movies: list[Movie],
    *,
    title: Optional[str] = None,
    genre: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    title_type: Optional[str] = None,
) -> list[Movie]:
    title_query = title.lower() if title else None
    genre_query = genre.lower() if genre else None
    type_query = title_type.lower() if title_type else None

    results: list[Movie] = []
    for movie in movies:
        if title_query and title_query not in movie.primary_title.lower():
            original = (movie.original_title or "").lower()
            if title_query not in original:
                continue
        if genre_query and genre_query not in {item.lower() for item in movie.genres}:
            continue
        if type_query and movie.title_type.lower() != type_query:
            continue
        if year_from is not None and (movie.start_year is None or movie.start_year < year_from):
            continue
        if year_to is not None and (movie.start_year is None or movie.start_year > year_to):
            continue
        results.append(movie)

    return sorted(results, key=_sort_key)


def _sort_key(movie: Movie) -> tuple[int, str]:
    year = movie.start_year if movie.start_year is not None else -1
    return (year, movie.primary_title.lower())
