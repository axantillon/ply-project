from __future__ import annotations

import re
from typing import Iterable, Optional

from .models import Movie

DECADE_RE = re.compile(r"\b(19|20)\d0s\b")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

GENRE_ALIASES = {
    "sci fi": "Sci-Fi",
    "sci-fi": "Sci-Fi",
    "scifi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "romance": "Romance",
    "comedy": "Comedy",
    "drama": "Drama",
    "action": "Action",
    "thriller": "Thriller",
    "crime": "Crime",
    "fantasy": "Fantasy",
    "animation": "Animation",
    "horror": "Horror",
    "documentary": "Documentary",
    "adventure": "Adventure",
    "mystery": "Mystery",
}

TITLE_TYPE_ALIASES = {
    "movie": "movie",
    "film": "movie",
    "series": "tvSeries",
    "show": "tvSeries",
    "short": "short",
    "tv movie": "tvMovie",
    "tv special": "tvSpecial",
    "video game": "videoGame",
}

STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "dark",
    "for",
    "from",
    "in",
    "like",
    "movie",
    "of",
    "set",
    "story",
    "that",
    "the",
    "with",
}


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
    genre_queries = parse_genre_filter(genre)
    type_query = title_type.lower() if title_type else None

    results: list[Movie] = []
    for movie in movies:
        if title_query and title_query not in movie.primary_title.lower():
            original = (movie.original_title or "").lower()
            if title_query not in original:
                continue
        movie_genres = {item.lower() for item in movie.genres}
        if genre_queries and not all(genre_query in movie_genres for genre_query in genre_queries):
            continue
        if type_query and movie.title_type.lower() != type_query:
            continue
        if year_from is not None and (movie.start_year is None or movie.start_year < year_from):
            continue
        if year_to is not None and (movie.start_year is None or movie.start_year > year_to):
            continue
        results.append(movie)

    return sorted(results, key=_sort_key)


def parse_genre_filter(value: Optional[str]) -> list[str]:
    if not value:
        return []
    parts = [part.strip().lower() for part in value.split(",")]
    return [part for part in parts if part]


def rank_movies_by_query(
    movies: Iterable[Movie],
    *,
    genres: Optional[list[str]] = None,
    title_type: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    keywords: Optional[list[str]] = None,
    limit: Optional[int] = 8,
) -> list[tuple[Movie, int]]:
    ranked: list[tuple[Movie, int]] = []
    for movie in movies:
        score = _match_score(
            movie,
            genres=genres or [],
            title_type=title_type,
            year_from=year_from,
            year_to=year_to,
            keywords=keywords or [],
        )
        ranked.append((movie, score))

    ranked.sort(key=lambda item: (-item[1], -_year_value(item[0]), item[0].primary_title.lower()))
    if limit is None:
        return ranked
    return ranked[:limit]


def _sort_key(movie: Movie) -> tuple[int, str]:
    year = movie.start_year if movie.start_year is not None else -1
    return (year, movie.primary_title.lower())


def _year_value(movie: Movie) -> int:
    return movie.start_year if movie.start_year is not None else -1


def _match_score(
    movie: Movie,
    *,
    genres: list[str],
    title_type: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    keywords: list[str],
) -> int:
    score = 0
    movie_genres = {genre.lower() for genre in movie.genres}

    for genre in genres:
        if genre.lower() in movie_genres:
            score += 3

    if title_type and movie.title_type.lower() == title_type.lower():
        score += 2

    if (
        year_from is not None
        and year_to is not None
        and movie.start_year is not None
        and year_from <= movie.start_year <= year_to
    ):
        score += 2

    search_text = " ".join(
        [
            movie.primary_title,
            movie.original_title or "",
            movie.title_type,
            " ".join(movie.genres),
        ]
    ).lower()
    for keyword in keywords:
        if keyword in search_text:
            score += 1

    return score


def infer_search_constraints(query: str) -> dict[str, Optional[object]]:
    lowered = query.lower()
    working = lowered

    genres: list[str] = []
    for alias, canonical in sorted(GENRE_ALIASES.items(), key=lambda item: -len(item[0])):
        if alias in working and canonical not in genres:
            genres.append(canonical)
            working = working.replace(alias, " ")

    title_type = None
    for alias, canonical in sorted(TITLE_TYPE_ALIASES.items(), key=lambda item: -len(item[0])):
        if alias in working:
            title_type = canonical
            working = working.replace(alias, " ")
            break

    year_from = None
    year_to = None
    match = DECADE_RE.search(lowered)
    if match:
        year_from = int(match.group(0)[:4])
        year_to = year_from + 9
        working = working.replace(match.group(0), " ")
    else:
        years = [int(value) for value in YEAR_RE.findall(lowered)]
        if len(years) >= 2:
            year_from, year_to = min(years), max(years)
        elif len(years) == 1:
            year_from = years[0]
            year_to = years[0]
        for year in years:
            working = working.replace(str(year), " ")

    keywords: list[str] = []
    for token in re.findall(r"[a-z0-9]+", working):
        if token in STOPWORDS or len(token) < 3:
            continue
        if token not in keywords:
            keywords.append(token)

    return {
        "genres": genres,
        "title_type": title_type,
        "year_from": year_from,
        "year_to": year_to,
        "keywords": keywords,
    }
