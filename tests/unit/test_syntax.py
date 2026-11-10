from __future__ import annotations

import pytest

from axiome.core.errors import ParseError
from axiome.reasoning.program import Constraint, Rule
from axiome.reasoning.syntax import Query, parse_atom, parse_program, parse_statement, tokenize
from axiome.reasoning.terms import Atom, Var


def test_parse_full_program() -> None:
    stmts = parse_program(
        """
        % comment
        is_a(cat, mammal).   # another comment
        [trans] is_a(X, Z) :- is_a(X, Y), is_a(Y, Z).
        ! cycle :- is_a(X, X).
        ?- is_a(X, animal), not is_a(X, bird).
        age(socrates, -70).
        name(x, "Socrates \\"the\\" wise").
        true.
        """
    )
    assert stmts[0] == Atom("is_a", ("cat", "mammal"))
    assert isinstance(stmts[1], Rule) and stmts[1].label == "trans"
    assert isinstance(stmts[2], Constraint) and stmts[2].name == "cycle"
    assert isinstance(stmts[3], Query) and stmts[3].body[1].negated
    assert stmts[4] == Atom("age", ("socrates", -70))
    assert stmts[5] == Atom("name", ("x", 'Socrates "the" wise'))
    assert stmts[6] == Atom("true")


def test_anonymous_variables_are_distinct() -> None:
    stmt = parse_statement("?- p(_, _)")
    assert isinstance(stmt, Query)
    a, b = stmt.body[0].atom.args
    assert isinstance(a, Var) and isinstance(b, Var) and a != b


def test_round_trip_str() -> None:
    text = '[r] p(X, "a b", 3) :- q(X), not r(X).'
    stmt = parse_statement(text)
    assert str(stmt) == text
    assert str(parse_statement(str(stmt))) == text
    assert str(parse_statement("?- p(X)")) == "?- p(X)."


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("p(X).", "parse.fact_not_ground"),
        ("p(a)", "parse.expected_token"),
        ("p(a,).", "parse.expected_term"),
        ('p("abc).', "parse.unterminated_string"),
        ('p("a\\q").', "parse.invalid_escape"),
        ("p(a) @", "parse.unexpected_char"),
        ("not(a).", "parse.reserved_negation"),
        ("[x] p(a).", "parse.label_only_on_rule"),
        ("P(a).", "parse.expected_name"),
        ("! C :- p(a).", "parse.expected_name"),
    ],
)
def test_errors_are_located(text: str, key: str) -> None:
    with pytest.raises(ParseError) as exc:
        parse_program(text)
    assert exc.value.message.key == key
    assert exc.value.line == 1
    assert str(exc.value).startswith("line 1, column")


def test_error_line_tracking() -> None:
    with pytest.raises(ParseError) as exc:
        parse_program("p(a).\n\n  q(b) r.")
    assert exc.value.line == 3


def test_parse_statement_requires_single() -> None:
    with pytest.raises(ParseError):
        parse_statement("p(a). q(b).")


def test_parse_atom_rejects_rules() -> None:
    with pytest.raises(ParseError):
        parse_atom("p(X) :- q(X)")
    assert tokenize("")[-1].kind == "EOF"
