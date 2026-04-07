from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request

from .datasets import load_catalog, resolve_dataset, select_semantic_backend
from .query import search_movies
from .semantic_search import semantic_search


def create_app(dataset_path: Optional[Path] = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    dataset = resolve_dataset(dataset_path)
    catalog = load_catalog(dataset)

    @app.get("/")
    def index():
        return render_template("index.html", dataset=str(dataset))

    @app.get("/api/stats")
    def stats():
        movies = list(catalog)
        years = [movie.start_year for movie in movies if movie.start_year is not None]
        genres = Counter(genre for movie in movies for genre in movie.genres)

        return jsonify(
            {
                "dataset": str(dataset),
                "movieCount": len(movies),
                "withSynopsisCount": sum(1 for movie in movies if movie.synopsis),
                "yearRange": [min(years), max(years)] if years else None,
                "topGenres": genres.most_common(8),
            }
        )

    @app.get("/api/find")
    def find():
        limit = _parse_limit(request.args.get("limit"), default=12)
        results = search_movies(
            list(catalog),
            title=_optional_text(request.args.get("title")),
            genre=_optional_text(request.args.get("genre")),
            title_type=_optional_text(request.args.get("title_type")),
            year_from=_optional_int(request.args.get("year_from")),
            year_to=_optional_int(request.args.get("year_to")),
        )[:limit]
        return jsonify({"dataset": str(dataset), "results": [_movie_payload(movie) for movie in results]})

    @app.get("/api/search")
    def search():
        query = _optional_text(request.args.get("q"))
        if not query:
            return jsonify({"error": "Missing search query"}), 400

        requested_backend = request.args.get("backend", "auto")
        backend = select_semantic_backend(requested_backend)
        limit = _parse_limit(request.args.get("limit"), default=8)
        cache_arg = _optional_text(request.args.get("cache"))
        cache_path = Path(cache_arg) if cache_arg else None
        output_dimensionality = _optional_int(request.args.get("output_dimensionality"))

        results = semantic_search(
            list(catalog),
            query,
            limit=limit,
            backend=backend,
            cache_path=cache_path,
            output_dimensionality=output_dimensionality,
        )
        return jsonify(
            {
                "dataset": str(dataset),
                "backend": backend,
                "results": [
                    {"score": score, "movie": _movie_payload(movie)}
                    for movie, score in results
                ],
            }
        )

    @app.get("/api/movie/<movie_id>")
    def show_movie(movie_id: str):
        movie = catalog.get(movie_id)
        if movie is None:
            return jsonify({"error": f"{movie_id} was not found"}), 404
        return jsonify({"dataset": str(dataset), "movie": _movie_payload(movie)})

    return app


def _movie_payload(movie):
    payload = movie.to_dict()
    payload["displayTitle"] = movie.primary_title
    payload["displayYear"] = movie.start_year if movie.start_year is not None else "Unknown"
    payload["genreText"] = ", ".join(movie.genres) if movie.genres else "n/a"
    return payload


def _optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or not value.strip():
        return None
    return int(value)


def _parse_limit(value: Optional[str], default: int) -> int:
    if value is None or not value.strip():
        return default
    return max(1, int(value))
