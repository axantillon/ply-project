# IMDb Movie Parser Project (PLY)

This project parses normalized movie JSON records with a PLY lexer/parser, stores them as in-memory `Movie` objects, and exposes both structured and natural-language search through a CLI.

## Project Layout

- `src/imdb_parser/parser.py`: PLY lexer/parser and parse helpers.
- `src/imdb_parser/models.py`: `Movie` dataclass and schema validation.
- `src/imdb_parser/catalog.py`: load JSON and JSONL movie datasets into memory.
- `src/imdb_parser/query.py`: deterministic movie search.
- `src/imdb_parser/semantic_search.py`: TF-IDF and Gemini-backed semantic retrieval.
- `scripts/build_imdb_medium_jsonl.py`: build a normalized JSONL dataset from IMDb `title.basics.tsv.gz`.
- `scripts/enrich_with_tmdb.py`: enrich the JSONL dataset with TMDb synopses.
- `scripts/movie_cli.py`: main CLI for validation, parsing, and querying.
- `scripts/movie_web.py`: one-page web UI for exploring the dataset in a browser.
- `scripts/validate_jsonl_with_parser.py`: validate many JSONL rows with the parser.
- `samples/`: complete sample input files for the parser.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Input Schema

Each movie file is a JSON object with this normalized shape:

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

## Build Dataset

```bash
python3 scripts/build_imdb_medium_jsonl.py --download --limit 15000
```

This writes `data/processed/imdb_movies_medium.jsonl`.

## Enrich With TMDb Synopses

Set a TMDb bearer token and run:

```bash
export TMDB_API_BEARER_TOKEN=your_token_here
python3 scripts/movie_cli.py enrich
```

This writes `data/processed/imdb_movies_enriched.jsonl` and caches fetched synopses at `data/processed/tmdb_overview_cache.json`.

## CLI Usage

The CLI auto-detects a default dataset in this order:

- `data/processed/imdb_movies_small_enriched.jsonl`
- `data/processed/imdb_movies_enriched.jsonl`
- `data/processed/imdb_movies_medium.jsonl`

Validate a sample file:

```bash
python3 scripts/movie_cli.py validate samples/sample1.json
```

Parse and print a file:

```bash
python3 scripts/movie_cli.py parse samples/sample1.json
```

Run structured search:

```bash
python3 scripts/movie_cli.py find --genre Sci-Fi --year-from 1990 --year-to 2010
```

Show one movie:

```bash
python3 scripts/movie_cli.py show --dataset samples tt0133093
```

Summarize the active dataset:

```bash
python3 scripts/movie_cli.py stats
```

## Web UI

Run the local web app:

```bash
python3 scripts/movie_web.py
```

Then open `http://127.0.0.1:8000`.

The page includes:

- natural-language search
- structured filtering
- a movie detail panel
- dataset statistics

Run natural-language search with the local TF-IDF backend:

```bash
python3 scripts/movie_cli.py search --dataset samples "dark sci-fi movie about simulated reality"
```

Run natural-language search with Gemini embeddings:

```bash
export GEMINI_API_KEY=your_key_here
python3 scripts/movie_cli.py search --backend gemini --cache data/processed/gemini_embedding_cache.json --dataset data/processed/imdb_movies_small_enriched.jsonl "a dark sci-fi movie about artificial reality and machines"
```

## Validate Dataset

```bash
python3 scripts/validate_jsonl_with_parser.py --max-lines 200
```
