#!/usr/bin/env python3
"""CLI for validating, parsing, enriching, and querying movie records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imdb_parser import parse_movie_json  # noqa: E402
from imdb_parser.datasets import load_catalog, resolve_dataset, select_semantic_backend  # noqa: E402
from imdb_parser.models import Movie  # noqa: E402
from imdb_parser.query import search_movies  # noqa: E402
from imdb_parser.semantic_search import semantic_search  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrich_with_tmdb import enrich_dataset  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="movie_cli",
        description="Explore parsed movie records from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    find_parser = subparsers.add_parser(
        "find",
        aliases=["filter"],
        help="Structured search by title, genre, year, or type",
    )
    _add_dataset_argument(find_parser)
    find_parser.add_argument("--title")
    find_parser.add_argument("--genre")
    find_parser.add_argument("--title-type")
    find_parser.add_argument("--year-from", type=int)
    find_parser.add_argument("--year-to", type=int)
    find_parser.add_argument("--limit", type=int, default=5)
    find_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    find_parser.set_defaults(func=cmd_find)

    search_parser = subparsers.add_parser(
        "search",
        aliases=["ask"],
        help="Natural-language search over the movie dataset",
    )
    _add_dataset_argument(search_parser)
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument(
        "--backend",
        choices=("auto", "tfidf", "gemini"),
        default="auto",
        help="Semantic search backend",
    )
    search_parser.add_argument("--cache", type=Path, help="Embedding cache file")
    search_parser.add_argument(
        "--output-dimensionality",
        type=int,
        help="Optional reduced embedding dimensionality for Gemini",
    )
    search_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    search_parser.set_defaults(func=cmd_search)

    show_parser = subparsers.add_parser("show", help="Show one movie by IMDb ID")
    _add_dataset_argument(show_parser)
    show_parser.add_argument("movie_id", help="IMDb ID, for example tt0133093")
    show_parser.add_argument("--json", action="store_true", help="Output the movie as JSON")
    show_parser.set_defaults(func=cmd_show)

    stats_parser = subparsers.add_parser("stats", help="Summarize the active movie dataset")
    _add_dataset_argument(stats_parser)
    stats_parser.add_argument("--json", action="store_true", help="Output stats as JSON")
    stats_parser.set_defaults(func=cmd_stats)

    validate_parser = subparsers.add_parser("validate", help="Validate a single movie JSON file")
    validate_parser.add_argument("path", type=Path)
    validate_parser.set_defaults(func=cmd_validate)

    parse_parser = subparsers.add_parser("parse", help="Parse a single movie JSON file")
    parse_parser.add_argument("path", type=Path)
    parse_parser.add_argument("--json", action="store_true", help="Output the parsed movie as JSON")
    parse_parser.set_defaults(func=cmd_parse)

    enrich_parser = subparsers.add_parser("enrich", help="Enrich a JSONL dataset with TMDb synopses")
    enrich_parser.add_argument(
        "--src",
        type=Path,
        default=Path("data/processed/imdb_movies_medium.jsonl"),
    )
    enrich_parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/imdb_movies_enriched.jsonl"),
    )
    enrich_parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/processed/tmdb_overview_cache.json"),
    )
    enrich_parser.add_argument("--delay-seconds", type=float, default=0.25)
    enrich_parser.set_defaults(func=cmd_enrich)

    legacy_semantic = subparsers.add_parser(
        "semantic-search",
        help=argparse.SUPPRESS,
    )
    _add_dataset_argument(legacy_semantic)
    legacy_semantic.add_argument("query")
    legacy_semantic.add_argument("--limit", type=int, default=5)
    legacy_semantic.add_argument("--backend", choices=("auto", "tfidf", "gemini"), default="auto")
    legacy_semantic.add_argument("--cache", type=Path)
    legacy_semantic.add_argument("--output-dimensionality", type=int)
    legacy_semantic.add_argument("--json", action="store_true")
    legacy_semantic.set_defaults(func=cmd_search)

    return parser


def _add_dataset_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Dataset path. Defaults to the best available processed dataset.",
    )
def cmd_validate(args: argparse.Namespace) -> int:
    parse_movie_json(args.path.read_text(encoding="utf-8"))
    print(f"Valid movie file: {args.path}")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    movie = parse_movie_json(args.path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(movie.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_movie_detail(movie)
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    dataset = resolve_dataset(args.dataset)
    catalog = load_catalog(dataset)
    results = search_movies(
        list(catalog),
        title=args.title,
        genre=args.genre,
        year_from=args.year_from,
        year_to=args.year_to,
        title_type=args.title_type,
    )[: args.limit]

    if args.json:
        print(json.dumps([movie.to_dict() for movie in results], ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        _print_ranked_movies(results)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    dataset = resolve_dataset(args.dataset)
    backend = select_semantic_backend(args.backend)
    catalog = load_catalog(dataset)
    results = semantic_search(
        list(catalog),
        args.query,
        limit=args.limit,
        backend=backend,
        cache_path=args.cache,
        output_dimensionality=args.output_dimensionality,
    )

    if args.json:
        payload = [
            {"score": score, "movie": movie.to_dict()}
            for movie, score in results
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        print(f"Semantic backend: {backend}")
        _print_ranked_movies((movie for movie, _ in results), scores=dict((movie.tconst, score) for movie, score in results))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    dataset = resolve_dataset(args.dataset)
    catalog = load_catalog(dataset)
    movie = catalog.get(args.movie_id)
    if movie is None:
        raise ValueError(f"Movie {args.movie_id} was not found in {dataset}")

    if args.json:
        print(json.dumps(movie.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        _print_movie_detail(movie)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    dataset = resolve_dataset(args.dataset)
    catalog = load_catalog(dataset)
    movies = list(catalog)
    years = [movie.start_year for movie in movies if movie.start_year is not None]
    genres = Counter(genre for movie in movies for genre in movie.genres)
    with_synopsis = sum(1 for movie in movies if movie.synopsis)

    payload = {
        "dataset": str(dataset),
        "movieCount": len(movies),
        "withSynopsisCount": with_synopsis,
        "yearRange": [min(years), max(years)] if years else None,
        "topGenres": genres.most_common(5),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        print(f"Movies: {payload['movieCount']}")
        print(f"With synopsis: {payload['withSynopsisCount']}")
        if payload["yearRange"] is not None:
            print(f"Year range: {payload['yearRange'][0]} to {payload['yearRange'][1]}")
        if payload["topGenres"]:
            print("Top genres:")
            for genre, count in payload["topGenres"]:
                print(f"- {genre}: {count}")
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    api_key = os.environ.get("TMDB_API_BEARER_TOKEN")
    if not api_key:
        raise RuntimeError("TMDB_API_BEARER_TOKEN must be set before running enrich")

    seen, enriched = enrich_dataset(
        args.src,
        args.out,
        api_key=api_key,
        cache_path=args.cache,
        delay_seconds=args.delay_seconds,
    )
    print(f"Wrote {seen} records to {args.out}; added synopses for {enriched} of them")
    return 0


def _print_ranked_movies(movies: Iterable[Movie], scores: Optional[dict[str, float]] = None) -> None:
    rendered = list(movies)
    if not rendered:
        print("No matches found.")
        return

    for index, movie in enumerate(rendered, start=1):
        year = movie.start_year if movie.start_year is not None else "unknown"
        genres = ", ".join(movie.genres) if movie.genres else "n/a"
        print(f"{index}. {movie.primary_title} ({year})")
        if scores and movie.tconst in scores:
            print(f"   {movie.tconst} | {genres} | score {scores[movie.tconst]:.3f}")
        else:
            print(f"   {movie.tconst} | {genres}")


def _print_movie_detail(movie: Movie) -> None:
    year = movie.start_year if movie.start_year is not None else "unknown"
    genres = ", ".join(movie.genres) if movie.genres else "n/a"
    runtime = f"{movie.runtime_minutes} min" if movie.runtime_minutes is not None else "unknown"
    print(f"{movie.primary_title} ({year})")
    print(f"ID: {movie.tconst}")
    print(f"Type: {movie.title_type}")
    print(f"Genres: {genres}")
    print(f"Runtime: {runtime}")
    if movie.synopsis:
        print("Synopsis:")
        print(movie.synopsis)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
