from __future__ import annotations

from axiome.i18n import msg
from axiome.reasoning.program import Program, Rule
from axiome.reasoning.syntax import parse_atom, parse_statement
from axiome.verification.epistemic import Assessment, Status
from axiome.verification.revision import revise
from tests.helpers import program_of

RULES = "is_a(X, Z) :- is_a(X, Y), is_a(Y, Z). ! disj :- is_a(X, A), disjoint(A, B), is_a(X, B)."


def a(status: Status) -> Assessment:
    return Assessment(status, (msg("reason.no_evidence"),))


def test_weak_fact_refuted_by_strong_ones() -> None:
    base = {
        parse_atom("is_a(cat, mammal)"): a(Status.PROVED),
        parse_atom("disjoint(mammal, bird)"): a(Status.CONFIRMED),
        parse_atom("is_a(cat, bird)"): a(Status.UNVERIFIED),
    }
    state = revise(program_of(RULES), base)
    culprit = parse_atom("is_a(cat, bird)")
    assert culprit in state.refuted and culprit not in state.model
    assert [c.resolved for c in state.conflicts] == [True]
    status = state.status(culprit)
    assert status is not None and status.status is Status.REFUTED


def test_equal_strength_is_contested_not_refuted() -> None:
    base = {
        parse_atom("is_a(x, a)"): a(Status.PLAUSIBLE),
        parse_atom("disjoint(a, b)"): a(Status.PROVED),
        parse_atom("is_a(x, b)"): a(Status.PLAUSIBLE),
    }
    state = revise(program_of(RULES), base)
    assert not state.refuted
    assert state.assessments[parse_atom("is_a(x, a)")].status is Status.CONTESTED
    assert state.assessments[parse_atom("is_a(x, b)")].status is Status.CONTESTED
    assert [c.resolved for c in state.conflicts] == [False]


def test_weakest_link_and_hypothesis_cap() -> None:
    base = {
        parse_atom("is_a(a, b)"): a(Status.PROVED),
        parse_atom("is_a(b, c)"): a(Status.PLAUSIBLE),
        parse_atom("p(a)"): a(Status.PROVED),
    }
    prog = program_of(RULES)
    assert revise(prog, base).assessments[parse_atom("is_a(a, c)")].status is Status.PLAUSIBLE
    hypothesis = parse_statement("q(X) :- p(X).", axiomatic=False)
    assert isinstance(hypothesis, Rule)
    state = revise(Program((*prog.rules, hypothesis), prog.constraints), base)
    assert state.assessments[parse_atom("q(a)")].status is Status.UNVERIFIED


def test_closed_world_cap() -> None:
    base = {parse_atom("p(a)"): a(Status.PROVED)}
    q = revise(program_of("q(X) :- p(X), not r(X)."), base).assessments[parse_atom("q(a)")]
    assert q.status is Status.PLAUSIBLE
    assert any(r.key == "reason.relies_on_absence" for r in q.reasons)


def test_refuted_by_evidence_excluded_upfront() -> None:
    state = revise(program_of("q(X) :- p(X)."), {parse_atom("p(a)"): a(Status.REFUTED)})
    assert parse_atom("q(a)") not in state.model
    status = state.status(parse_atom("p(a)"))
    assert status is not None and status.status is Status.REFUTED
    assert state.status(parse_atom("z(a)")) is None


def test_cascading_refutation() -> None:
    base = {
        parse_atom("is_a(x, a)"): a(Status.PROVED),
        parse_atom("is_a(y, a)"): a(Status.PROVED),
        parse_atom("disjoint(a, b)"): a(Status.PROVED),
        parse_atom("is_a(x, b)"): a(Status.UNVERIFIED),
        parse_atom("is_a(y, b)"): a(Status.UNVERIFIED),
    }
    state = revise(program_of(RULES), base)
    assert set(state.refuted) == {parse_atom("is_a(x, b)"), parse_atom("is_a(y, b)")}
    assert all(c.resolved for c in state.conflicts)
