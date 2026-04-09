from __future__ import annotations

from collections import Counter
from pathlib import Path
import threading
from typing import Optional

from flask import Flask, jsonify, render_template, request

from .datasets import load_catalog, resolve_dataset
from .query import infer_search_constraints, rank_movies_by_query, search_movies

RESULTS_PER_PAGE = 10


def create_app(dataset_path: Optional[Path] = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    dataset = resolve_dataset(dataset_path)
    state = {
        "status": "loading",
        "error": None,
        "catalog": None,
        "movies": [],
    }
    state_lock = threading.Lock()

    def load_dataset_in_background() -> None:
        try:
            catalog = load_catalog(dataset)
            movies = list(catalog)
        except Exception as exc:  # pragma: no cover - startup boundary
            with state_lock:
                state["status"] = "error"
                state["error"] = str(exc)
            return

        with state_lock:
            state["catalog"] = catalog
            state["movies"] = movies
            state["status"] = "ready"

    threading.Thread(target=load_dataset_in_background, daemon=True).start()

    def snapshot_state():
        with state_lock:
            return {
                "status": state["status"],
                "error": state["error"],
                "catalog": state["catalog"],
                "movies": list(state["movies"]),
            }

    def require_ready():
        snapshot = snapshot_state()
        if snapshot["status"] == "ready":
            return snapshot
        payload = {
            "dataset": str(dataset),
            "status": snapshot["status"],
        }
        if snapshot["error"]:
            payload["error"] = snapshot["error"]
        return jsonify(payload), 503

    @app.get("/")
    def index():
        static_dir = Path(app.static_folder)
        styles_version = int((static_dir / "styles.css").stat().st_mtime)
        app_version = int((static_dir / "app.js").stat().st_mtime)
        return render_template(
            "index.html",
            dataset=str(dataset),
            styles_version=styles_version,
            app_version=app_version,
        )

    @app.get("/api/status")
    def status():
        snapshot = snapshot_state()
        payload = {
            "dataset": str(dataset),
            "status": snapshot["status"],
        }
        if snapshot["status"] == "ready":
            movies = snapshot["movies"]
            years = [movie.start_year for movie in movies if movie.start_year is not None]
            payload["movieCount"] = len(movies)
            payload["yearRange"] = [min(years), max(years)] if years else None
        if snapshot["error"]:
            payload["error"] = snapshot["error"]
        return jsonify(payload)

    @app.get("/api/stats")
    def stats():
        snapshot = require_ready()
        if not isinstance(snapshot, dict):
            return snapshot
        movies = snapshot["movies"]
        years = [movie.start_year for movie in movies if movie.start_year is not None]
        genres = Counter(genre for movie in movies for genre in movie.genres)

        return jsonify(
            {
                "dataset": str(dataset),
                "movieCount": len(movies),
                "recordType": "IMDb movies",
                "yearRange": [min(years), max(years)] if years else None,
                "topGenres": genres.most_common(8),
            }
        )

    @app.get("/api/find")
    def find():
        snapshot = require_ready()
        if not isinstance(snapshot, dict):
            return snapshot
        movies = snapshot["movies"]
        page = _parse_page(request.args.get("page"))
        results = search_movies(
            movies,
            title=_optional_text(request.args.get("title")),
            genre=_optional_text(request.args.get("genre")),
            title_type=_optional_text(request.args.get("title_type")),
            year_from=_optional_int(request.args.get("year_from")),
            year_to=_optional_int(request.args.get("year_to")),
        )
        total_results = len(results)
        paged_results, total_pages = _paginate(results, page)
        return jsonify(
            {
                "dataset": str(dataset),
                "page": page,
                "perPage": RESULTS_PER_PAGE,
                "totalResults": total_results,
                "totalPages": total_pages,
                "results": [_movie_payload(movie) for movie in paged_results],
            }
        )

    @app.get("/api/search")
    def search():
        snapshot = require_ready()
        if not isinstance(snapshot, dict):
            return snapshot
        movies = snapshot["movies"]
        query = _optional_text(request.args.get("q"))
        if not query:
            return jsonify({"error": "Missing search query"}), 400

        inferred = infer_search_constraints(query)
        manual_filters = request.args.get("manual_filters") == "1"
        explicit_genre = _optional_text(request.args.get("genre"))
        inferred_genres = inferred["genres"]
        effective_genres = (
            [part.strip() for part in explicit_genre.split(",") if part.strip()]
            if explicit_genre
            else ([] if manual_filters else inferred_genres)
        )
        hard_genre = ", ".join(effective_genres) if effective_genres else None
        title_type = _optional_text(request.args.get("title_type"))
        if title_type is None and not manual_filters:
            title_type = inferred["title_type"]
        year_from = _optional_int(request.args.get("year_from"))
        if year_from is None and not manual_filters:
            year_from = inferred["year_from"]
        year_to = _optional_int(request.args.get("year_to"))
        if year_to is None and not manual_filters:
            year_to = inferred["year_to"]
        title = _optional_text(request.args.get("title"))

        page = _parse_page(request.args.get("page"))
        scoped_movies = search_movies(
            movies,
            title=title,
            genre=hard_genre,
            title_type=title_type,
            year_from=year_from,
            year_to=year_to,
        )
        ranked_results = rank_movies_by_query(
            scoped_movies,
            genres=effective_genres,
            title_type=title_type,
            year_from=year_from,
            year_to=year_to,
            keywords=inferred["keywords"],
            limit=None,
        )
        total_results = len(ranked_results)
        paged_results, total_pages = _paginate(ranked_results, page)

        return jsonify(
            {
                "dataset": str(dataset),
                "scopeCount": len(scoped_movies),
                "page": page,
                "perPage": RESULTS_PER_PAGE,
                "totalResults": total_results,
                "totalPages": total_pages,
                "interpretedQuery": {
                    "genres": inferred_genres,
                    "titleType": title_type,
                    "yearFrom": year_from,
                    "yearTo": year_to,
                    "keywords": inferred["keywords"],
                },
                "effectiveFilters": {
                    "genre": ", ".join(effective_genres),
                    "titleType": title_type,
                    "yearFrom": year_from,
                    "yearTo": year_to,
                    "title": title,
                },
                "results": [
                    _movie_payload(movie, score=score)
                    for movie, score in paged_results
                ],
            }
        )

    @app.get("/api/movie/<movie_id>")
    def show_movie(movie_id: str):
        snapshot = require_ready()
        if not isinstance(snapshot, dict):
            return snapshot
        movie = snapshot["catalog"].get(movie_id)
        if movie is None:
            return jsonify({"error": f"{movie_id} was not found"}), 404
        return jsonify({"dataset": str(dataset), "movie": _movie_payload(movie)})

    return app


def _movie_payload(movie, score: Optional[int] = None):
    payload = movie.to_dict()
    payload["displayTitle"] = movie.primary_title
    payload["displayYear"] = movie.start_year if movie.start_year is not None else "Unknown"
    payload["genreText"] = ", ".join(movie.genres) if movie.genres else "n/a"
    if score is not None:
        payload["matchScore"] = score
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


def _parse_page(value: Optional[str]) -> int:
    if value is None or not value.strip():
        return 1
    return max(1, int(value))


def _paginate(items, page: int):
    total_results = len(items)
    total_pages = max(1, (total_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    return items[start:end], total_pages
