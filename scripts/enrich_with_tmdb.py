#!/usr/bin/env python3
"""Enrich a JSONL movie dataset with TMDb overviews keyed by IMDb ID."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple


TMDB_FIND_URL = "https://api.themoviedb.org/3/find/{imdb_id}?external_source=imdb_id"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{movie_id}"


def load_cache(path: Path) -> Dict[str, Optional[str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path: Path, cache: Dict[str, Optional[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def fetch_json(url: str, api_key: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_overview(imdb_id: str, api_key: str) -> Optional[str]:
    find_url = TMDB_FIND_URL.format(imdb_id=urllib.parse.quote(imdb_id))
    find_payload = fetch_json(find_url, api_key)
    movie_results = find_payload.get("movie_results", [])
    if not movie_results:
        return None

    movie_id = movie_results[0]["id"]
    movie_url = TMDB_MOVIE_URL.format(movie_id=movie_id)
    movie_payload = fetch_json(movie_url, api_key)
    overview = movie_payload.get("overview")
    return overview.strip() if isinstance(overview, str) and overview.strip() else None


def enrich_dataset(
    src: Path,
    dst: Path,
    *,
    api_key: str,
    cache_path: Path,
    delay_seconds: float,
) -> Tuple[int, int]:
    cache = load_cache(cache_path)
    seen = 0
    enriched = 0

    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8") as input_handle, dst.open("w", encoding="utf-8") as output_handle:
        for line in input_handle:
            stripped = line.strip()
            if not stripped:
                continue
            seen += 1
            record = json.loads(stripped)
            imdb_id = record["tconst"]

            if imdb_id not in cache:
                try:
                    cache[imdb_id] = fetch_overview(imdb_id, api_key)
                except urllib.error.HTTPError as exc:
                    raise RuntimeError(f"TMDb request failed for {imdb_id}: {exc}") from exc
                save_cache(cache_path, cache)
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

            overview = cache.get(imdb_id)
            if overview:
                record["synopsis"] = overview
                enriched += 1
            output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    save_cache(cache_path, cache)
    return seen, enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path("data/processed/imdb_movies_medium.jsonl"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/imdb_movies_enriched.jsonl"),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("data/processed/tmdb_overview_cache.json"),
    )
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    args = parser.parse_args()

    api_key = os.environ.get("TMDB_API_BEARER_TOKEN")
    if not api_key:
        raise RuntimeError("TMDB_API_BEARER_TOKEN must be set to enrich the dataset")

    seen, enriched = enrich_dataset(
        args.src,
        args.out,
        api_key=api_key,
        cache_path=args.cache,
        delay_seconds=args.delay_seconds,
    )
    print(f"Wrote {seen} records to {args.out}; added synopses for {enriched} of them")


if __name__ == "__main__":
    main()
