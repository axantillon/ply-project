# Programming Assignment 1, Part 2

## Movie Parser With PLY

Course: CS 3383  
Team: David A. / Andres A. / Sol G.  
Repository: `https://github.com/axantillon/ply-project`  
Video Demo: `<PASTE_VIDEO_URL_HERE>`

Prepared with assistance from Codex (GPT-5.4).

## Contents

- [Project Overview](#project-overview)
- [Repository Walkthrough](#repository-walkthrough)
- [Architecture](#architecture)
- [Design Approach](#design-approach)
- [End-to-End Flow](#end-to-end-flow)
- [Grammar and Parser Summary](#grammar-and-parser-summary)
- [In-Memory Representation](#in-memory-representation)
- [Functionality Built on Top of Parsed Data](#functionality-built-on-top-of-parsed-data)
- [Sample Inputs](#sample-inputs)
- [Validation and Testing](#validation-and-testing)
- [How To Explore the Project](#how-to-explore-the-project)
- [Context-Free Grammar (CFG)](#context-free-grammar-cfg)
- [Partial Canonical Collection](#partial-canonical-collection)
- [Important Note About CFG vs. Code](#important-note-about-cfg-vs-code)
- [Conclusion](#conclusion)

## Project Overview

This project implements a movie parser using Python Lex-Yacc (PLY). The parser reads normalized JSON movie records, validates them, stores the parsed results in memory as Python objects, and exposes useful functionality through both a command-line interface and a local web interface.

The project can be understood in two complementary ways:

- as a parser implementation with a formal grammar
- as a small application built on top of parsed movie data

At a high level, the solution is designed as a pipeline:

1. read a movie record from a file or dataset
2. parse the JSON structure with PLY
3. validate that the parsed structure represents a valid movie
4. store the result as `Movie` objects in memory
5. expose operations over those objects through CLI commands and the web app

## Repository Walkthrough

The main files for evaluation are:

- [`src/imdb_parser/parser.py`](src/imdb_parser/parser.py): PLY lexer and parser
- [`src/imdb_parser/models.py`](src/imdb_parser/models.py): movie object model and semantic validation
- [`src/imdb_parser/catalog.py`](src/imdb_parser/catalog.py): in-memory collection of parsed movies
- [`src/imdb_parser/query.py`](src/imdb_parser/query.py): structured search on parsed data
- [`src/imdb_parser/webapp.py`](src/imdb_parser/webapp.py): local web interface
- [`scripts/movie_cli.py`](scripts/movie_cli.py): main command-line interface
- [`samples/sample1.json`](samples/sample1.json), [`samples/sample2.json`](samples/sample2.json), [`samples/sample3.json`](samples/sample3.json): valid input files
- [`samples/invalid_sample.json`](samples/invalid_sample.json): invalid sample for rejection testing
- [`tests/test_parser.py`](tests/test_parser.py): parser tests

## Architecture

The architecture is intentionally simple and layered so that each part has one responsibility.

### 1. Parsing Layer

[`src/imdb_parser/parser.py`](src/imdb_parser/parser.py) contains the lexer and grammar rules. Its responsibility is to convert input text into Python values according to the CFG.

This layer answers the question:

- is the input structurally valid according to the grammar?

Its output is a parsed Python object, typically a dictionary at the top level.

### 2. Domain Validation Layer

[`src/imdb_parser/models.py`](src/imdb_parser/models.py) turns the parsed dictionary into a `Movie` object. This is where movie-specific constraints are enforced.

This layer answers the question:

- even if the JSON structure is valid, is it a valid movie record for this project?

Keeping this separate from the parser made the implementation easier to reason about. The grammar stays focused on syntax, and the model stays focused on meaning and correctness of the movie schema.

### 3. Catalog Layer

[`src/imdb_parser/catalog.py`](src/imdb_parser/catalog.py) loads one file, a directory of files, or a JSONL dataset into memory as a `MovieCatalog`.

This layer answers the question:

- how do individual parsed movies become a collection the rest of the application can use?

This is the layer that makes searching, statistics, and lookups possible over multiple parsed records.

### 4. Query and Retrieval Layer

The application exposes two forms of retrieval:

- [`src/imdb_parser/query.py`](src/imdb_parser/query.py) for deterministic filtering by title, genre, type, and year
- [`src/imdb_parser/semantic_search.py`](src/imdb_parser/semantic_search.py) for natural-language search over the parsed movie data

This layer answers the question:

- once movies are in memory, how can the user find the relevant ones?

### 5. Interface Layer

The same parser and movie model are exposed through two interfaces:

- [`scripts/movie_cli.py`](scripts/movie_cli.py) for command-line validation, parsing, and search
- [`src/imdb_parser/webapp.py`](src/imdb_parser/webapp.py) plus [`scripts/movie_web.py`](scripts/movie_web.py) for a browser-based interface

This keeps the architecture modular. The parser logic is not duplicated for the CLI and the web app. Both interfaces depend on the same core parser and catalog logic.

## Design Approach

The parser and validation logic are intentionally split into two layers.

### 1. Syntactic Parsing

The grammar implemented in PLY recognizes a JSON-style object language. It supports:

- objects
- arrays
- strings
- numbers
- booleans
- null

This layer determines whether the input is syntactically valid.

### 2. Semantic Validation

After parsing succeeds, the resulting Python structure is validated as a movie record. This layer checks constraints such as:

- required fields must exist
- `tconst` must begin with `tt`
- `genres` must be a list of strings
- optional fields must have valid types when present

This separation is deliberate. The CFG describes the accepted syntax, while the Python model layer applies movie-specific rules after parsing.

## End-to-End Flow

The easiest way to understand the design is to follow one request from input to output.

### Example: Parsing One Movie File

When a user runs:

```bash
python3 scripts/movie_cli.py parse samples/sample1.json
```

the system behaves as follows:

1. the CLI reads the file contents
2. `parse_movie_json` in [`src/imdb_parser/parser.py`](src/imdb_parser/parser.py) uses the PLY lexer and grammar to parse the text
3. the parsed dictionary is passed into `Movie.from_mapping` in [`src/imdb_parser/models.py`](src/imdb_parser/models.py)
4. semantic rules are checked and a `Movie` object is created
5. the CLI prints the movie in a readable form

This flow is important because it shows the separation of concerns:

- parsing checks structure
- the model checks movie validity
- the interface formats the result for the user

### Example: Searching a Dataset

When a user runs a dataset command such as:

```bash
python3 scripts/movie_cli.py find --dataset samples --genre Sci-Fi
```

the flow is:

1. the CLI resolves the dataset path
2. `MovieCatalog.from_path` in [`src/imdb_parser/catalog.py`](src/imdb_parser/catalog.py) loads the files and parses each movie into memory
3. the resulting `Movie` objects are stored in a `MovieCatalog`
4. `search_movies` in [`src/imdb_parser/query.py`](src/imdb_parser/query.py) filters the in-memory movies
5. the CLI renders the matching results

The web app follows the same core pattern. The difference is only the interface layer: browser requests instead of terminal commands.

## Grammar and Parser Summary

The parser is implemented in [`src/imdb_parser/parser.py`](src/imdb_parser/parser.py) using:

- tokens: `STRING`, `NUMBER`, `TRUE`, `FALSE`, `NULL`
- literals: `{`, `}`, `[`, `]`, `:`, `,`
- productions for objects, arrays, members, pairs, and values

The start symbol is:

```text
movie -> object
```

This means each movie file is parsed as one top-level object.

## In-Memory Representation

Once a valid input is parsed, the record is stored as a `Movie` object. Multiple parsed movies can be loaded into a `MovieCatalog`, which supports iteration, lookup, and search over the dataset.

This satisfies the requirement that parsed information must remain in memory using objects or data structures.

The choice to represent movies explicitly as domain objects makes the rest of the project easier to understand. Search, display, and statistics do not need to manipulate raw JSON directly. They operate on structured `Movie` instances instead.

## Functionality Built on Top of Parsed Data

The application supports more than the minimum required functionality. It can:

- validate a movie file
- parse and display a movie
- search by title, genre, type, and year range
- show a movie by IMDb ID
- summarize dataset statistics
- perform natural-language movie search

## Sample Inputs

The repository includes these complete valid sample inputs:

- [`samples/sample1.json`](samples/sample1.json)
- [`samples/sample2.json`](samples/sample2.json)
- [`samples/sample3.json`](samples/sample3.json)

The repository also includes:

- [`samples/invalid_sample.json`](samples/invalid_sample.json)

The invalid sample demonstrates that bad input is rejected by the parser and validation layer.

## Validation and Testing

Validation in the current implementation is concentrated on the parser and schema-validation path. It was checked through automated parser tests and direct execution of the CLI commands that exercise the main parsing flow.

### Automated Parser Tests

The unit tests in [`tests/test_parser.py`](tests/test_parser.py) check:

- valid movie parsing
- nested JSON preservation
- invalid schema rejection
- missing required field rejection
- malformed JSON rejection

Run:

```bash
python3 -m unittest tests.test_parser
```

These tests target the parser and validation behavior directly. They do not attempt to provide broad automated coverage for the CLI interface or the web interface.

### Direct Validation Examples

Valid sample:

```bash
python3 scripts/movie_cli.py validate samples/sample1.json
```

Invalid sample:

```bash
python3 scripts/movie_cli.py validate samples/invalid_sample.json
```

Parse and display:

```bash
python3 scripts/movie_cli.py parse samples/sample1.json
```

Search the sample set:

```bash
python3 scripts/movie_cli.py find --dataset samples --genre Sci-Fi
```

These command examples verify that valid input can be parsed and rendered, invalid input is rejected, and parsed records can be queried once loaded into memory.

## How To Explore the Project

The project can be explored in the following order:

1. Open the repository link at the top of this page.
2. Review [`src/imdb_parser/parser.py`](src/imdb_parser/parser.py) for the PLY grammar.
3. Review [`src/imdb_parser/models.py`](src/imdb_parser/models.py) for semantic movie validation.
4. Review the sample files in [`samples/`](samples/).
5. Run the CLI commands listed above.
6. Optionally start the browser interface:

```bash
python3 scripts/movie_web.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Context-Free Grammar (CFG)

The CFG used for this project is:

```text
S' -> movie
movie -> object
object -> { members_opt }
members_opt -> members
members_opt -> epsilon
members -> pair
members -> members , pair
pair -> STRING : value
array -> [ elements_opt ]
elements_opt -> elements
elements_opt -> epsilon
elements -> value
elements -> elements , value
value -> STRING
value -> NUMBER
value -> object
value -> array
value -> TRUE
value -> FALSE
value -> NULL
```

### CFG Explanation

- `movie -> object`
  A movie file is represented as one JSON object.

- `object -> { members_opt }`
  An object is enclosed in curly braces and may contain zero or more members.

- `members_opt -> members | epsilon`
  An object may contain members or may be empty.

- `members -> pair | members , pair`
  Members are one or more comma-separated key-value pairs.

- `pair -> STRING : value`
  Each pair contains a string key and a value.

- `array -> [ elements_opt ]`
  Arrays are enclosed in square brackets and may contain zero or more elements.

- `elements_opt -> elements | epsilon`
  An array may contain elements or may be empty.

- `elements -> value | elements , value`
  Array contents are one or more comma-separated values.

- `value -> STRING | NUMBER | object | array | TRUE | FALSE | NULL`
  A value may be a primitive literal or a nested object or array.

## Partial Canonical Collection

Below is a compact presentation of the first 10 LALR(1) states included in the project material.

### Closure of Initial State

```text
i0:
S' -> . movie
movie -> . object
object -> . { members_opt }
```

Transitions from `i0`:

- `movie -> i1`
- `object -> i2`
- `{ -> i3`

### First 10 States

```text
i1:
S' -> movie .

i2:
movie -> object .

i3:
object -> { . members_opt }
members_opt -> . members
members_opt -> . epsilon
members -> . pair
members -> . members , pair
pair -> . STRING : value

i4:
object -> { members_opt . }

i5:
members_opt -> members .
members -> members . , pair

i6:
members_opt -> epsilon .

i7:
members -> pair .

i8:
pair -> STRING . : value

i9:
object -> { members_opt } .

i10:
members -> members , . pair
pair -> . STRING : value
```

This partial collection is sufficient to show the beginning of the parser construction and satisfies the assignment requirement to include at least 10 states.

## First and Follow Notes

The grammar was also analyzed using First and Follow sets in the supporting project material. Those sets help justify the parser construction and the relationship among:

- `movie`
- `object`
- `members_opt`
- `members`
- `pair`
- `array`
- `elements_opt`
- `elements`
- `value`

## Important Note About CFG vs. Code

The CFG describes the syntactic structure accepted by the parser. The implementation then applies movie-specific semantic constraints in Python after parsing. This means:

- the CFG defines valid structural form
- the PLY parser implements that structural form
- the `Movie` model enforces movie-specific validity rules

This matches the actual implementation strategy used in the repository.

## Conclusion

This submission delivers a complete parser-based movie project with:

- a formal grammar
- a working PLY lexer/parser
- in-memory movie objects and catalog storage
- valid and invalid sample inputs
- automated tests
- practical functionality built on parsed data

The result is both a parser and an application that demonstrates the usefulness of the parsed information.
