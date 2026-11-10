from __future__ import annotations

import pytest

from axiome.core.errors import KnowledgeError, ProgramError
from axiome.reasoning.engine import evaluate
from axiome.reasoning.program import Program
from axiome.reasoning.syntax import parse_atom
from axiome.reasoning.terms import Atom, Var
from tests.helpers import body, model

TRANS = "t(X, Z) :- e(X, Y), t(Y, Z). t(X, Y) :- e(X, Y)."


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
        "bird(tweety). bird(pingu). penguin(pingu)."
        "flies(X) :- bird(X), not abnormal(X). abnormal(X) :- penguin(X)."
    )
    assert parse_atom("flies(tweety)") in m
    assert parse_atom("flies(pingu)") not in m
    assert m.justification(parse_atom("flies(tweety)")).absent == (parse_atom("abnormal(tweety)"),)


def test_query_bindings_and_dedup() -> None:
    m = model(TRANS + "e(a, b). e(b, c). e(a, c).")
    assert [dict(a.bindings)[Var("X")] for a in m.query(body("t(a, X)"))] == ["b", "c"]
    assert m.query(body("t(a, c)"))[0].bindings == ()
    assert m.query(body("t(c, X)")) == []
    neg = m.query(body("e(a, X), not e(X, c)"))
    assert [dict(a.bindings)[Var("X")] for a in neg] == ["c"]


def test_query_safety() -> None:
    with pytest.raises(ProgramError):
        model("p(a).").query(body("p(a), not q(Y)"))


def test_proof_and_support() -> None:
    m = model(TRANS + "e(a, b). e(b, c).")
    goal = parse_atom("t(a, c)")
    proof = m.proof(goal)
    assert proof.rule is not None and proof.fact == goal
    assert m.support(goal) == {parse_atom("e(a, b)"), parse_atom("e(b, c)")}
    assert m.is_base(parse_atom("e(a, b)"))
    with pytest.raises(KnowledgeError):
        m.justification(parse_atom("t(z, z)"))


def test_constraints_report_violations() -> None:
    m = model("! cycle :- t(X, X). " + TRANS + "e(a, b). e(b, a).")
    assert {v.constraint.name for v in m.violations} == {"cycle"}
    assert len(m.violations) == 2  # t(a,a) and t(b,b)


def test_non_ground_base_rejected() -> None:
    with pytest.raises(ProgramError):
        evaluate(Program(), [Atom("p", (Var("X"),))])


def test_justification_is_canonical_minimum() -> None:
    # two possible derivations for p(a): the smallest rule index wins
    m = model("p(X) :- q(X). p(X) :- r(X). q(a). r(a).")
    assert m.justification(parse_atom("p(a)")).rule_index == 0
