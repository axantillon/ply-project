 # -----------------------------------------------------------------------------
# calc.py
#
# Initial PLY parser for JSON data (movie objects from IMDB-style datasets).
# -----------------------------------------------------------------------------

import json

import ply.lex as lex
import ply.yacc as yacc

tokens = (
    "STRING",
    "NUMBER",
    "TRUE",
    "FALSE",
    "NULL",
)

# JSON punctuation literals
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
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


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
    p[0] = dict([p[1]])


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
    pass


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")


parser = yacc.yacc(start="movie")

if __name__ == "__main__":
    while True:
        try:
            s = input("json-movie > ")
        except EOFError:
            break
        if not s.strip():
            continue
        result = parser.parse(s, lexer=lexer)
        print(result)
