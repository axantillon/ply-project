#!/usr/bin/env python3
"""CLI for validating, parsing, building, and querying movie records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imdb_parser import parse_movie_json  # noqa: E402
from imdb_parser.datasets import load_catalog, resolve_dataset  # noqa: E402
from imdb_parser.models import Movie  # noqa: E402
from imdb_parser.query import infer_search_constraints, rank_movies_by_query, search_movies  # noqa: E402
from build_imdb_medium_jsonl import IMDB_BASICS_URL, build_jsonl, maybe_download  # noqa: E402


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
        help="Interpret a natural-language prompt into structured movie search",
    )
    _add_dataset_argument(search_parser)
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    search_parser.set_defaults(func=cmd_search)

    explain_parser = subparsers.add_parser(
        "explain-query",
        help="Show how a natural-language query is interpreted into structured constraints",
    )
    explain_parser.add_argument("query")
    explain_parser.set_defaults(func=cmd_explain_query)

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

    build_parser_cmd = subparsers.add_parser(
        "build-dataset",
        help="Build a normalized movie dataset from IMDb title.basics",
    )
    build_parser_cmd.add_argument("--raw", type=Path, default=Path("data/raw/title.basics.tsv.gz"))
    build_parser_cmd.add_argument(
        "--download",
        action="store_true",
        help="Download title.basics.tsv.gz if missing",
    )
    build_parser_cmd.add_argument(
        "--limit",
        type=int,
        help="Optional record limit. Omit to build the full dataset.",
    )
    build_parser_cmd.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/imdb_movies_full.jsonl"),
    )
    build_parser_cmd.set_defaults(func=cmd_build_dataset)

    return parser


def _add_dataset_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Dataset path. Defaults to the best available processed dataset.",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    raw_text = args.path.read_text(encoding="utf-8")
    movie = parse_movie_json(raw_text)
    genres = ", ".join(movie.genres) if movie.genres else "n/a"
    year = movie.start_year if movie.start_year is not None else "unknown"
    runtime = f"{movie.runtime_minutes} min" if movie.runtime_minutes is not None else "unknown"
    print("Input preview:")
    print(_preview_text(raw_text))
    print("Validation passed")
    print(f"File: {args.path}")
    print(f"ID: {movie.tconst}")
    print(f"Title: {movie.primary_title}")
    print(f"Type: {movie.title_type}")
    print(f"Year: {year}")
    print(f"Genres: {genres}")
    print(f"Runtime: {runtime}")
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
    catalog = load_catalog(dataset)
    inferred = infer_search_constraints(args.query)
    movies = list(catalog)
    scoped_movies = search_movies(
        movies,
        genre=", ".join(inferred["genres"]) if inferred["genres"] else None,
        title_type=inferred["title_type"],
        year_from=inferred["year_from"],
        year_to=inferred["year_to"],
    )
    ranked_results = rank_movies_by_query(
        scoped_movies,
        genres=inferred["genres"],
        title_type=inferred["title_type"],
        year_from=inferred["year_from"],
        year_to=inferred["year_to"],
        keywords=inferred["keywords"],
        limit=args.limit,
    )

    if args.json:
        payload = {
            "query": args.query,
            "interpretedQuery": {
                "genres": inferred["genres"],
                "titleType": inferred["title_type"],
                "yearFrom": inferred["year_from"],
                "yearTo": inferred["year_to"],
                "keywords": inferred["keywords"],
            },
            "results": [{"score": score, "movie": movie.to_dict()} for movie, score in ranked_results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        _print_query_interpretation(inferred)
        _print_ranked_movies(results_to_movies(ranked_results), scores={movie.tconst: score for movie, score in ranked_results})
    return 0


def cmd_explain_query(args: argparse.Namespace) -> int:
    inferred = infer_search_constraints(args.query)
    genres = ", ".join(inferred["genres"]) if inferred["genres"] else "none"
    title_type = inferred["title_type"] or "none"
    if inferred["year_from"] is None and inferred["year_to"] is None:
        year_range = "none"
    elif inferred["year_from"] == inferred["year_to"]:
        year_range = str(inferred["year_from"])
    else:
        year_range = f"{inferred['year_from']} to {inferred['year_to']}"
    keywords = ", ".join(inferred["keywords"]) if inferred["keywords"] else "none"

    print("Query interpretation")
    print(f'Input: "{args.query}"')
    print(f"Genres: {genres}")
    print(f"Title type: {title_type}")
    print(f"Year range: {year_range}")
    print(f"Keywords: {keywords}")
    return 0


def results_to_movies(results):
    return (movie for movie, _ in results)


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
    payload = {
        "dataset": str(dataset),
        "movieCount": len(movies),
        "recordType": "IMDb movies",
        "yearRange": [min(years), max(years)] if years else None,
        "topGenres": genres.most_common(5),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Dataset: {dataset}")
        print(f"Movies: {payload['movieCount']}")
        print(f"Record type: {payload['recordType']}")
        if payload["yearRange"] is not None:
            print(f"Year range: {payload['yearRange'][0]} to {payload['yearRange'][1]}")
        if payload["topGenres"]:
            print("Top genres:")
            for genre, count in payload["topGenres"]:
                print(f"- {genre}: {count}")
    return 0


def cmd_build_dataset(args: argparse.Namespace) -> int:
    if args.download:
        maybe_download(IMDB_BASICS_URL, args.raw)
    elif not args.raw.exists():
        raise FileNotFoundError(f"Raw file not found: {args.raw}. Use --download.")

    count = build_jsonl(args.raw, args.out, args.limit)
    label = "full dataset" if args.limit is None else f"{count} records"
    print(f"Wrote {label} to {args.out}")
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


def _preview_text(raw_text: str, limit: int = 220) -> str:
    compact = " ".join(raw_text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _print_query_interpretation(inferred: dict[str, object]) -> None:
    genres = ", ".join(inferred["genres"]) if inferred["genres"] else "none"
    title_type = inferred["title_type"] or "none"
    if inferred["year_from"] is None and inferred["year_to"] is None:
        year_range = "none"
    elif inferred["year_from"] == inferred["year_to"]:
        year_range = str(inferred["year_from"])
    else:
        year_range = f"{inferred['year_from']} to {inferred['year_to']}"
    keywords = ", ".join(inferred["keywords"]) if inferred["keywords"] else "none"
    print("Interpreted query:")
    print(f"- Genres: {genres}")
    print(f"- Title type: {title_type}")
    print(f"- Year range: {year_range}")
    print(f"- Keywords: {keywords}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - CLI boundary
        if getattr(args, "command", None) == "validate":
            try:
                raw_text = args.path.read_text(encoding="utf-8")
                print("Input preview:", file=sys.stderr)
                print(_preview_text(raw_text), file=sys.stderr)
            except Exception:
                pass
            print("Validation failed", file=sys.stderr)
            print(f"File: {args.path}", file=sys.stderr)
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
