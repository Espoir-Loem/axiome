from __future__ import annotations

import pytest

from axiome.core.errors import ParseError
from axiome.reasoning.program import Constraint, Rule
from axiome.reasoning.syntax import Query, parse_atom, parse_program, parse_statement, tokenize
from axiome.reasoning.terms import Atom, Var


def test_parse_full_program() -> None:
    stmts = parse_program(
        """
        % commentaire
        est_un(chat, mammifère).   # autre commentaire
        [trans] est_un(X, Z) :- est_un(X, Y), est_un(Y, Z).
        ! cycle :- est_un(X, X).
        ?- est_un(X, animal), non est_un(X, oiseau).
        age(socrate, -70).
        nom(x, "Socrate \\"le\\" sage").
        vrai.
        """
    )
    assert stmts[0] == Atom("est_un", ("chat", "mammifère"))
    assert isinstance(stmts[1], Rule) and stmts[1].label == "trans"
    assert isinstance(stmts[2], Constraint) and stmts[2].name == "cycle"
    assert isinstance(stmts[3], Query) and stmts[3].body[1].negated
    assert stmts[4] == Atom("age", ("socrate", -70))
    assert stmts[5] == Atom("nom", ("x", 'Socrate "le" sage'))
    assert stmts[6] == Atom("vrai")


def test_anonymous_variables_are_distinct() -> None:
    stmt = parse_statement("?- p(_, _)")
    assert isinstance(stmt, Query)
    a, b = stmt.body[0].atom.args
    assert isinstance(a, Var) and isinstance(b, Var) and a != b


def test_round_trip_str() -> None:
    text = '[r] p(X, "a b", 3) :- q(X), non r(X).'
    stmt = parse_statement(text)
    assert str(stmt) == text
    assert str(parse_statement(str(stmt))) == text
    assert str(parse_statement("?- p(X)")) == "?- p(X)."


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("p(X).", "clos"),
        ("p(a)", "« . » attendu"),
        ("p(a,).", "terme attendu"),
        ('p("abc).', "chaîne non terminée"),
        ('p("a\\q").', "échappement"),
        ("p(a) @", "caractère inattendu"),
        ("non(a).", "réservé"),
        ("[x] p(a).", "étiquette"),
        ("P(a).", "nom"),
        ("! C :- p(a).", "nom"),
    ],
)
def test_errors_are_located(text: str, fragment: str) -> None:
    with pytest.raises(ParseError) as exc:
        parse_program(text)
    assert fragment in str(exc.value)
    assert exc.value.line == 1


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
