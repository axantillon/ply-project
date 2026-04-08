# Project Status

## Latest Additions

- The web UI was simplified into a minimal, centered single-composer interface.
- Search results now open movie details in a modal instead of rendering an inline detail pane at the bottom of the list.
- The modal and template reload path were stabilized so local frontend changes show up correctly during development.
- Result rendering was adjusted to prevent horizontal overflow from long descriptions and metadata.
- Parser-only tests were added in `tests/test_parser.py` to validate grammar and schema behavior independently from the CLI and web UI.
- The raw full IMDb movie dataset was built into `data/processed/imdb_movies_medium.jsonl`.
- Default dataset selection now prefers the larger processed dataset over the tiny sample dataset when available.
- The web app now keeps a lazy in-process TF-IDF index so repeated semantic searches on the full dataset are faster than rebuilding the index each time.
- The semantic search surface was simplified to TF-IDF only.

## Current State

- Full dataset size: `742,654` movie rows.
- Full dataset synopsis coverage: `0`.
- Small enriched dataset synopsis coverage: partial only.
- Semantic search currently works over title, original title, type, year, and genres.
- Gemini and other embedding-model paths are no longer part of the intended product direction.

## Why TF-IDF Only

- The full dataset does not contain synopses, so embedding models would mostly learn from the same sparse metadata already available to TF-IDF.
- That means a local embedding model would add complexity, model downloads, and indexing cost without solving the real quality problem.
- For the current dataset, the simplest honest implementation is TF-IDF semantic search plus structured filters.

## Remaining Work

- Improve natural-language query handling so prompts map more cleanly onto existing structured filters.
- Add a small set of API or CLI smoke tests for search flows, separate from the parser unit tests.
- Clean up documentation so README and submission notes fully match the current product scope.
- Decide whether generated large dataset artifacts should stay local only or be excluded from final tracked changes.
- Do a final QA pass on the web UI using representative full-dataset searches.

## Explicit Non-Goals

- Video deliverable work.
- Canonical collection work.
- CFG deliverable work.
- Full-dataset synopsis enrichment.
- Gemini or other embedding-based semantic search for this submission.
