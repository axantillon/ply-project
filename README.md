# Movie Parser Project (PLY)

This repository is organized as a submission-ready movie parser project for Programming Assignment 1, Part 2. It implements a JSON-based movie parser in PLY, stores parsed data in memory as Python objects, and provides both CLI and web interfaces for exploring the parsed records.

The main submission page is:

- `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`

That page is intended to be rendered directly on GitHub. It contains the project walkthrough, CFG, partial canonical collection, and the repository/video links used for submission.

## Architecture

The project is split into four layers:

1. Parsing layer
   - PLY tokenizes and parses one movie JSON object.
   - The parser reduces input directly into Python data structures.
2. Validation and in-memory model layer
   - Parsed mappings are converted into `Movie` objects.
   - A `MovieCatalog` stores many parsed `Movie` objects in memory.
3. Query and application layer
   - Structured search filters parsed movies by genre, years, title, and title type.
   - Natural-language search is interpreted into structured constraints and then executed over the same in-memory catalog.
4. Interface layer
   - A CLI exposes validation, parsing, and query commands.
   - A small Flask web app exposes the same functionality through a browser UI.

The important architectural point is that the parser and validation logic are implemented in Python, and every interface sits on top of the same parsed `Movie` objects.

## Repository Map

### Submission and top-level documents

- `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`
  - Main submission report.
  - Explains the parser, CFG, canonical collection, and how to demonstrate the project.
- `PROGRAMMING_ASSIGNMENT_1_PART_2.md`
  - Assignment instructions that define the required deliverables.
- `README.md`
  - Repository guide, setup steps, architecture summary, and demo commands.
- `AGENTS.md`
  - Collaboration rules for humans and coding agents working in this repository.

### Core Python package: `src/imdb_parser/`

- `src/imdb_parser/__init__.py`
  - Package marker for the parser project.

- `src/imdb_parser/parser.py`
  - Core PLY implementation.
  - Defines lexer tokens, grammar rules, parse actions, and public parsing functions.
  - This is the main file to inspect for the formal parser.

- `src/imdb_parser/models.py`
  - Defines the `Movie` dataclass.
  - Performs movie-specific semantic validation after syntactic parsing succeeds.
  - Converts raw parsed mappings into typed in-memory objects.

- `src/imdb_parser/catalog.py`
  - Loads one file, many files, or a JSONL dataset into memory.
  - Stores parsed `Movie` objects in a `MovieCatalog`.
  - Provides lookup and iteration over the in-memory collection.

- `src/imdb_parser/query.py`
  - Implements search functionality over parsed movies.
  - Contains structured filtering and natural-language query interpretation.
  - This is where prompts like `scifi 2010s` become explicit genre/year constraints.

- `src/imdb_parser/datasets.py`
  - Resolves which dataset file should be used by default.
  - Contains helper logic for loading the chosen dataset path into the catalog layer.

- `src/imdb_parser/webapp.py`
  - Flask application for the browser demo.
  - Starts the server, loads the dataset, exposes JSON API endpoints, and serves the HTML page.
  - Uses the same parser, catalog, and query logic as the CLI.

### Web UI files

- `src/imdb_parser/templates/index.html`
  - Main browser page template rendered by Flask.
  - Defines the layout for the query composer, manual filters, results list, pagination, and detail modal.

- `src/imdb_parser/static/app.js`
  - Client-side browser behavior.
  - Sends search requests to the Flask API, renders results dynamically, syncs interpreted filters into the visible controls, and manages pagination and the detail modal.
  - This file does not parse movies. It only drives the optional web interface.

- `src/imdb_parser/static/styles.css`
  - Styling for the browser interface.
  - Controls the page layout, spacing, form appearance, results cards, and modal presentation.

### Generated parser artifacts

- `src/imdb_parser/parser.out`
  - Generated PLY parser report.
  - Useful for grammar debugging and canonical-table inspection.
  - Not the source of truth for the grammar.

- `src/imdb_parser/parsetab.py`
  - Generated PLY parse table cache.
  - Speeds parser startup.
  - Not where grammar changes should be made.

### Command-line entry points and utilities: `scripts/`

- `scripts/movie_cli.py`
  - Main CLI for the project.
  - Supports validation, parsing, structured search, natural-language query explanation, and dataset-oriented commands.
  - This is the easiest interface for demonstrating parser behavior directly.

- `scripts/movie_web.py`
  - Small launcher script for the Flask web app.
  - Starts the browser interface locally.

- `scripts/validate_jsonl_with_parser.py`
  - Utility script to validate many JSONL records with the parser.
  - Useful for checking larger datasets against the parser implementation.

- `scripts/build_imdb_medium_jsonl.py`
  - Dataset-building utility for generating processed IMDb JSONL files.
  - Supports preparing medium-sized or full local datasets for the project.

### Samples and tests

- `samples/sample1.json`
  - Valid sample movie record.

- `samples/sample2.json`
  - Valid sample movie record.

- `samples/sample3.json`
  - Valid sample movie record.

- `samples/invalid_sample.json`
  - Invalid sample used to show parser/model rejection behavior.

- `tests/test_parser.py`
  - Automated tests for parsing and validation behavior.
  - Confirms accepted inputs and rejected inputs behave as expected.

### Data directories

- `data/raw/`
  - Raw downloaded dataset inputs, such as IMDb source files.

- `data/processed/`
  - Processed JSONL datasets used by the CLI and web app.
  - Typical files include `imdb_movies_small.jsonl`, `imdb_movies_medium.jsonl`, and `imdb_movies_full.jsonl`.

## What To Read First

If you want to understand the project quickly, follow this order:

1. `src/imdb_parser/parser.py`
2. `src/imdb_parser/models.py`
3. `src/imdb_parser/catalog.py`
4. `src/imdb_parser/query.py`
5. `scripts/movie_cli.py`
6. `samples/`
7. `tests/test_parser.py`
8. `src/imdb_parser/webapp.py`
9. `src/imdb_parser/templates/index.html`
10. `src/imdb_parser/static/app.js`

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

Explain how a natural-language query will be interpreted:

```bash
python3 scripts/movie_cli.py explain-query "scifi 2010s"
```

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
python3 scripts/movie_cli.py parse samples/sample1.json --json
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

For a full demo with the larger dataset:

```bash
python3 scripts/movie_web.py --dataset data/processed/imdb_movies_full.jsonl
```

## Datasets

The CLI can operate on sample files or on processed JSONL datasets under `data/processed/`. The default dataset selection order is:

1. `data/processed/imdb_movies_full.jsonl`
2. `data/processed/imdb_movies_medium.jsonl`
3. `data/processed/imdb_movies_small.jsonl`

You can override this with `--dataset`.

## How The Interfaces Relate To The Parser

The parser is the core of the project. Everything else uses it.

- The CLI reads movie JSON files, parses them with PLY, validates them into `Movie` objects, and prints or searches the resulting in-memory objects.
- The web app loads the same parsed movie records into memory and exposes search through a browser UI.
- The JavaScript file in `src/imdb_parser/static/app.js` does not replace the parser. It only provides an interactive front end for the Flask API.

In other words:

- `parser.py` and `models.py` define what a valid movie record is
- `catalog.py` stores parsed records in memory
- `query.py` implements operations over those parsed records
- `movie_cli.py` and `webapp.py` are two different ways to use the same parsed data

## Notes For Submission

For grading, the most useful path is:

1. Open `PROGRAMMING_ASSIGNMENT_1_PART_2_REPORT.md`.
2. Follow the repository and video links there.
3. Review the CFG and the partial canonical collection in that page.
4. Run the example commands in this README or in the submission report.
