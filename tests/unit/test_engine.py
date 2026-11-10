from __future__ import annotations

import pytest

from axiome.core.errors import KnowledgeError, ProgramError
from axiome.reasoning.engine import evaluate
from axiome.reasoning.program import Program
from axiome.reasoning.syntax import parse_atom, parse_statement
from axiome.reasoning.terms import Atom, Var
from tests.helpers import model

TRANS = "t(X, Z) :- e(X, Y), t(Y, Z). t(X, Y) :- e(X, Y)."


def body(text: str):  # type: ignore[no-untyped-def]
    return parse_statement(f"?- {text}").body  # type: ignore[union-attr]


def test_transitive_closure() -> None:
    m = model(TRANS + "e(a, b). e(b, c). e(c, d).")
    assert parse_atom("t(a, d)") in m
    assert parse_atom("t(d, a)") not in m
    assert len([f for f in m.facts() if f.predicate == "t"]) == 6


def test_cycles_terminate() -> None:
    m = model(TRANS + "e(a, b). e(b, a).")
    assert parse_atom("t(a, a)") in m and parse_atom("t(b, b)") in m


def test_stratified_negation() -> None:
    m = model(
        "oiseau(tweety). oiseau(pingu). manchot(pingu)."
        "vole(X) :- oiseau(X), non anormal(X). anormal(X) :- manchot(X)."
    )
    assert parse_atom("vole(tweety)") in m
    assert parse_atom("vole(pingu)") not in m
    j = m.justification(parse_atom("vole(tweety)"))
    assert j.absent == (parse_atom("anormal(tweety)"),)


def test_query_bindings_and_dedup() -> None:
    m = model(TRANS + "e(a, b). e(b, c). e(a, c).")
    answers = m.query(body("t(a, X)"))
    assert [dict(a.bindings)[Var("X")] for a in answers] == ["b", "c"]
    assert m.query(body("t(a, c)"))[0].bindings == ()
    assert m.query(body("t(c, X)")) == []
    neg = m.query(body("e(a, X), non e(X, c)"))
    assert [dict(a.bindings)[Var("X")] for a in neg] == ["c"]


def test_query_safety() -> None:
    m = model("p(a).")
    with pytest.raises(ProgramError):
        m.query(body("p(a), non q(Y)"))


def test_proof_and_support() -> None:
    m = model(TRANS + "e(a, b). e(b, c).")
    goal = parse_atom("t(a, c)")
    proof = m.proof(goal)
    assert proof.rule is not None and proof.fact == goal
    leaves = m.support(goal)
    assert leaves == {parse_atom("e(a, b)"), parse_atom("e(b, c)")}
    assert m.is_base(parse_atom("e(a, b)"))
    with pytest.raises(KnowledgeError):
        m.justification(parse_atom("t(z, z)"))


def test_constraints_report_violations() -> None:
    m = model("! cycle :- t(X, X). " + TRANS + "e(a, b). e(b, a).")
    names = {v.constraint.name for v in m.violations}
    assert names == {"cycle"}
    assert len(m.violations) == 2  # t(a,a) et t(b,b)


def test_non_ground_base_rejected() -> None:
    with pytest.raises(ProgramError):
        evaluate(Program(), [Atom("p", (Var("X"),))])


def test_justification_is_canonical_minimum() -> None:
    # deux dérivations possibles pour p(a) : la règle d'indice le plus petit gagne
    m = model("p(X) :- q(X). p(X) :- r(X). q(a). r(a).")
    assert m.justification(parse_atom("p(a)")).rule_index == 0
