#!/usr/bin/env python3
"""Validate a JSONL file with the project's PLY parser."""

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imdb_parser import parse_movie_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data/processed/imdb_movies_medium.jsonl"),
        help="JSONL file to validate",
    )
    parser.add_argument("--max-lines", type=int, default=100, help="Number of lines to validate")
    args = parser.parse_args()

    ok = 0
    with args.file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i > args.max_lines:
                break
            parse_movie_json(line.strip())
            ok += 1

    print(f"Validated {ok} lines from {args.file}")


if __name__ == "__main__":
    main()
