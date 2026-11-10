from __future__ import annotations

import pytest

from axiome.reasoning.terms import Atom, Literal, Var, format_term, substitute, term_key, unify

X, Y = Var("X"), Var("Y")


def test_format_term_quotes_only_when_needed() -> None:
    assert format_term("cat") == "cat"
    assert format_term("Cat") == '"Cat"'
    assert format_term("O(n log n)") == '"O(n log n)"'
    assert format_term('a"b\\c\n') == '"a\\"b\\\\c\\n"'
    assert format_term("not") == '"not"'
    assert format_term(-3) == "-3"
    assert format_term(X) == "X"


def test_bool_is_rejected() -> None:
    with pytest.raises(TypeError):
        format_term(True)


def test_term_key_total_order() -> None:
    assert sorted([X, "b", 2, "a", 1], key=term_key) == [1, 2, "a", "b", X]


def test_atom_properties() -> None:
    a = Atom("p", (X, "a", X, Y))
    assert not a.is_ground()
    assert a.variables() == (X, Y)
    assert str(a) == "p(X, a, X, Y)"
    assert str(Atom("true")) == "true"
    assert str(Literal(a, negated=True)).startswith("not ")


def test_unify_and_substitute() -> None:
    assert unify(Atom("p", (X, X)), Atom("p", ("a", "a")), {}) == {X: "a"}
    assert unify(Atom("p", (X, X)), Atom("p", ("a", "b")), {}) is None
    assert unify(Atom("p", (X,)), Atom("q", ("a",)), {}) is None
    assert unify(Atom("p", (1,)), Atom("p", ("1",)), {}) is None  # distinct types
    assert unify(Atom("p", (X, Y)), Atom("p", (Y, "a")), {}) == {X: Y, Y: "a"}
    assert substitute(Atom("p", (X, Y)), {X: Y, Y: "a"}) == Atom("p", ("a", "a"))
