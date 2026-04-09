# Movie Parser Project (PLY)

This repository is organized as a submission-ready movie parser project for Programming Assignment 1, Part 2. It implements a JSON-based movie parser in PLY, stores parsed data in memory as Python objects, and provides both CLI and web interfaces for exploring the parsed records.

The main submission page is:

- `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`

That page is intended to be rendered directly on GitHub. It contains the project walkthrough, CFG, partial canonical collection, and the repository/video links used for submission.

## Repository Structure

The repository is intentionally organized around the parts that matter for evaluation:

- `src/imdb_parser/`: parser, models, catalog, search, and web app code
- `scripts/`: command-line entry points and dataset utilities
- `samples/`: valid and invalid example movie inputs
- `tests/`: parser tests
- `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`: the submission report

## Core Files

The main files to review are:

- `src/imdb_parser/parser.py`: PLY lexer and parser rules
- `src/imdb_parser/models.py`: `Movie` model and semantic validation
- `src/imdb_parser/catalog.py`: in-memory catalog loading
- `src/imdb_parser/query.py`: structured query logic
- `src/imdb_parser/semantic_search.py`: semantic retrieval backends
- `src/imdb_parser/webapp.py`: Flask web app
- `scripts/movie_cli.py`: primary CLI entry point
- `scripts/movie_web.py`: local web launcher
- `tests/test_parser.py`: parser and validation tests

The repository intentionally avoids putting submission guidance, assignment text, and implementation code at the same level unless those files are directly useful for grading.

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use MiniLM search, `sentence-transformers` may download the model on first use.

## Input Format

Each movie input is a JSON object with fields like:

```json
{
  "tconst": "tt0133093",
  "titleType": "movie",
  "primaryTitle": "The Matrix",
  "originalTitle": "The Matrix",
  "isAdult": false,
  "startYear": 1999,
  "endYear": null,
  "runtimeMinutes": 136,
  "genres": ["Action", "Sci-Fi"],
  "synopsis": "A hacker discovers reality is a simulation."
}
```

The parser accepts the JSON structure, and the model layer enforces movie-specific constraints such as required fields and field types.

## Quick Start

Validate a valid sample:

```bash
python3 scripts/movie_cli.py validate samples/sample1.json
```

Validate an invalid sample:

```bash
python3 scripts/movie_cli.py validate samples/invalid_sample.json
```

Parse and display one movie:

```bash
python3 scripts/movie_cli.py parse samples/sample1.json
```

Search the sample dataset:

```bash
python3 scripts/movie_cli.py find --dataset samples --genre Sci-Fi
```

Run the parser tests:

```bash
python3 -m unittest tests.test_parser
```

Start the local web app:

```bash
python3 scripts/movie_web.py
```

Then open `http://127.0.0.1:8000`.

## Datasets

The CLI can operate on sample files or on processed JSONL datasets under `data/processed/`. The default dataset selection order is:

1. `data/processed/imdb_movies_full.jsonl`
2. `data/processed/imdb_movies_medium.jsonl`
3. `data/processed/imdb_movies_small.jsonl`

You can override this with `--dataset`.

## Notes For Submission

For grading, the most useful path is:

1. Open `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`.
2. Follow the repository and video links there.
3. Review the CFG and the partial canonical collection in that page.
4. Run the example commands in this README or in the submission report.
