#!/usr/bin/env python3
"""Build a medium-sized JSONL file from IMDb non-commercial title.basics data."""

import argparse
import csv
import gzip
import json
import urllib.request
from pathlib import Path


IMDB_BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"


def maybe_download(url: str, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dst)


def nullish(value: str):
    return None if value == "\\N" else value


def build_jsonl(src_gz: Path, dst_jsonl: Path, limit: int | None) -> int:
    count = 0
    dst_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(src_gz, "rt", encoding="utf-8", newline="") as f_in, dst_jsonl.open(
        "w", encoding="utf-8"
    ) as f_out:
        reader = csv.DictReader(f_in, delimiter="\t")
        for row in reader:
            if row["titleType"] != "movie":
                continue

            start_year = nullish(row["startYear"])
            end_year = nullish(row["endYear"])
            runtime = nullish(row["runtimeMinutes"])
            genres = nullish(row["genres"])

            obj = {
                "tconst": row["tconst"],
                "titleType": row["titleType"],
                "primaryTitle": nullish(row["primaryTitle"]),
                "originalTitle": nullish(row["originalTitle"]),
                "isAdult": bool(int(row["isAdult"])) if row["isAdult"].isdigit() else None,
                "startYear": int(start_year) if start_year else None,
                "endYear": int(end_year) if end_year else None,
                "runtimeMinutes": int(runtime) if runtime else None,
                "genres": genres.split(",") if genres else [],
                "synopsis": None,
            }
            f_out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1

            if limit is not None and count >= limit:
                break

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        help="Number of movie records to write. Omit to write every movie in title.basics.tsv.gz.",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/raw/title.basics.tsv.gz"),
        help="Path to title.basics.tsv.gz",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/imdb_movies_medium.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download title.basics.tsv.gz if missing",
    )
    args = parser.parse_args()

    if args.download:
        maybe_download(IMDB_BASICS_URL, args.raw)
    elif not args.raw.exists():
        raise FileNotFoundError(f"Raw file not found: {args.raw}. Use --download.")

    count = build_jsonl(args.raw, args.out, args.limit)
    print(f"Wrote {count} records to {args.out}")


if __name__ == "__main__":
    main()
