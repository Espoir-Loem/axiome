"""Mathematical properties of the engine, checked on generated inputs.

Hypothesis generates graphs; the result must match an independent reference
computation (Floyd-Warshall) and be invariant under permutation.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from axiome.reasoning.engine import evaluate
from axiome.reasoning.syntax import parse_statement
from axiome.reasoning.terms import Atom, format_term
from tests.helpers import program_of

NODES = st.sampled_from(["a", "b", "c", "d", "e", "f"])
EDGES = st.lists(st.tuples(NODES, NODES), max_size=14, unique=True)
PROGRAM = program_of("t(X, Y) :- e(X, Y). t(X, Z) :- t(X, Y), e(Y, Z).")


def reference_closure(edges: list[tuple[str, str]]) -> set[tuple[str, str]]:
    nodes = sorted({n for e in edges for n in e})
    reach = {(a, b) for a, b in edges}
    for k in nodes:
        for i in nodes:
            for j in nodes:
                if (i, k) in reach and (k, j) in reach:
                    reach.add((i, j))
    return reach


@settings(max_examples=150, deadline=None)
@given(EDGES)
def test_closure_matches_reference(edges: list[tuple[str, str]]) -> None:
    m = evaluate(PROGRAM, [Atom("e", e) for e in edges])
    got = {f.args for f in m.facts() if f.predicate == "t"}
    assert got == reference_closure(edges)


@settings(max_examples=100, deadline=None)
@given(EDGES, st.randoms(use_true_random=False))
def test_model_and_proofs_invariant_under_permutation(edges, rnd) -> None:  # type: ignore[no-untyped-def]
    facts = [Atom("e", e) for e in edges]
    shuffled = list(facts)
    rnd.shuffle(shuffled)
    m1, m2 = evaluate(PROGRAM, facts), evaluate(PROGRAM, shuffled)
    assert m1.facts() == m2.facts()
    for f in m1.facts():
        assert m1.justification(f) == m2.justification(f)


@settings(max_examples=100, deadline=None)
@given(EDGES)
def test_every_derived_fact_has_valid_proof(edges: list[tuple[str, str]]) -> None:
    m = evaluate(PROGRAM, [Atom("e", e) for e in edges])
    for f in m.facts():
        assert m.support(f) <= {Atom("e", e) for e in edges}


TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r"), max_size=12
)


@settings(max_examples=200, deadline=None)
@given(st.lists(st.one_of(TEXT, st.integers(-(10**6), 10**6)), min_size=1, max_size=4))
def test_format_parse_round_trip(args: list[str | int]) -> None:
    atom = Atom("p", tuple(args))
    text = f"p({', '.join(format_term(a) for a in args)})"
    assert str(atom) == text
    assert parse_statement(text) == atom
