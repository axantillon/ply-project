# -----------------------------------------------------------------------------
# parser.py
#
# PLY-based parser for normalized movie JSON objects.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ply.lex as lex
import ply.yacc as yacc

from .models import Movie, MovieValidationError


class MovieParseError(ValueError):
    """Raised when the input cannot be parsed as a movie object."""


tokens = (
    "STRING",
    "NUMBER",
    "TRUE",
    "FALSE",
    "NULL",
)

literals = ["{", "}", "[", "]", ":", ","]
t_ignore = " \t\r"


def t_STRING(t):
    r'"([^"\\]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"'
    t.value = json.loads(t.value)
    return t


def t_NUMBER(t):
    r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?"
    text = t.value
    if "." in text or "e" in text.lower():
        t.value = float(text)
    else:
        t.value = int(text)
    return t


def t_TRUE(t):
    r"true"
    t.value = True
    return t


def t_FALSE(t):
    r"false"
    t.value = False
    return t


def t_NULL(t):
    r"null"
    t.value = None
    return t


def t_newline(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


def t_error(t):
    raise MovieParseError(f"Illegal character {t.value[0]!r} at position {t.lexpos}")


lexer = lex.lex()


def p_movie(p):
    "movie : object"
    p[0] = p[1]


def p_object(p):
    "object : '{' members_opt '}'"
    p[0] = p[2]


def p_members_opt_members(p):
    "members_opt : members"
    p[0] = p[1]


def p_members_opt_empty(p):
    "members_opt : empty"
    p[0] = {}


def p_members_single(p):
    "members : pair"
    key, value = p[1]
    p[0] = {key: value}


def p_members_multi(p):
    "members : members ',' pair"
    p[0] = p[1]
    key, value = p[3]
    p[0][key] = value


def p_pair(p):
    "pair : STRING ':' value"
    p[0] = (p[1], p[3])


def p_array(p):
    "array : '[' elements_opt ']'"
    p[0] = p[2]


def p_elements_opt_elements(p):
    "elements_opt : elements"
    p[0] = p[1]


def p_elements_opt_empty(p):
    "elements_opt : empty"
    p[0] = []


def p_elements_single(p):
    "elements : value"
    p[0] = [p[1]]


def p_elements_multi(p):
    "elements : elements ',' value"
    p[0] = p[1]
    p[0].append(p[3])


def p_value(p):
    """value : STRING
             | NUMBER
             | object
             | array
             | TRUE
             | FALSE
             | NULL"""
    p[0] = p[1]


def p_empty(p):
    "empty :"


def p_error(p):
    if p is None:
        raise MovieParseError("Syntax error at EOF")
    raise MovieParseError(f"Syntax error at token {p.type} with value {p.value!r}")


_THIS_DIR = Path(__file__).resolve().parent
parser = yacc.yacc(start="movie", outputdir=str(_THIS_DIR))


def parse_movie_json_raw(text: str) -> dict[str, Any]:
    result = parser.parse(text, lexer=lexer.clone())
    if not isinstance(result, dict):
        raise MovieParseError("Top-level JSON value must be an object")
    return result


def parse_movie_json(text: str) -> Movie:
    payload = parse_movie_json_raw(text)
    try:
        return Movie.from_mapping(payload)
    except MovieValidationError as exc:
        raise MovieParseError(str(exc)) from exc


if __name__ == "__main__":
    while True:
        try:
            line = input("json-movie > ")
        except EOFError:
            break
        if not line.strip():
            continue
        try:
            movie = parse_movie_json(line)
        except MovieParseError as exc:
            print(f"error: {exc}")
            continue
        print(movie)
