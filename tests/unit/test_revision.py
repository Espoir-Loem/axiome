from __future__ import annotations

from axiome.reasoning.program import Program
from axiome.reasoning.syntax import parse_atom, parse_statement
from axiome.verification.epistemic import Assessment, Status
from axiome.verification.revision import revise
from tests.helpers import program_of

RULES = (
    "est_un(X, Z) :- est_un(X, Y), est_un(Y, Z)."
    "! disj :- est_un(X, A), disjoint(A, B), est_un(X, B)."
)


def a(status: Status) -> Assessment:
    return Assessment(status, ("test",))


def test_weak_fact_refuted_by_strong_ones() -> None:
    base = {
        parse_atom("est_un(chat, mammifère)"): a(Status.PROVED),
        parse_atom("disjoint(mammifère, oiseau)"): a(Status.CONFIRMED),
        parse_atom("est_un(chat, oiseau)"): a(Status.UNVERIFIED),
    }
    state = revise(program_of(RULES), base)
    assert parse_atom("est_un(chat, oiseau)") in state.refuted
    assert parse_atom("est_un(chat, oiseau)") not in state.model
    assert [c.resolved for c in state.conflicts] == [True]
    assert state.status(parse_atom("est_un(chat, oiseau)")).status is Status.REFUTED  # type: ignore[union-attr]


def test_equal_strength_is_contested_not_refuted() -> None:
    base = {
        parse_atom("est_un(x, a)"): a(Status.PLAUSIBLE),
        parse_atom("disjoint(a, b)"): a(Status.PROVED),
        parse_atom("est_un(x, b)"): a(Status.PLAUSIBLE),
    }
    state = revise(program_of(RULES), base)
    assert not state.refuted
    assert state.assessments[parse_atom("est_un(x, a)")].status is Status.CONTESTED
    assert state.assessments[parse_atom("est_un(x, b)")].status is Status.CONTESTED
    assert [c.resolved for c in state.conflicts] == [False]


def test_weakest_link_and_hypothesis_cap() -> None:
    base = {
        parse_atom("est_un(a, b)"): a(Status.PROVED),
        parse_atom("est_un(b, c)"): a(Status.PLAUSIBLE),
        parse_atom("p(a)"): a(Status.PROVED),
    }
    prog = program_of(RULES)
    state = revise(prog, base)
    assert state.assessments[parse_atom("est_un(a, c)")].status is Status.PLAUSIBLE

    hypo = parse_statement("q(X) :- p(X).", axiomatic=False)
    prog2 = Program((*prog.rules, hypo), prog.constraints)  # type: ignore[arg-type]
    state2 = revise(prog2, base)
    assert state2.assessments[parse_atom("q(a)")].status is Status.UNVERIFIED


def test_closed_world_cap() -> None:
    base = {parse_atom("p(a)"): a(Status.PROVED)}
    state = revise(program_of("q(X) :- p(X), non r(X)."), base)
    q = state.assessments[parse_atom("q(a)")]
    assert q.status is Status.PLAUSIBLE
    assert any("monde clos" in r for r in q.reasons)


def test_refuted_by_evidence_excluded_upfront() -> None:
    base = {parse_atom("p(a)"): a(Status.REFUTED)}
    state = revise(program_of("q(X) :- p(X)."), base)
    assert parse_atom("q(a)") not in state.model
    assert state.status(parse_atom("p(a)")).status is Status.REFUTED  # type: ignore[union-attr]
    assert state.status(parse_atom("z(a)")) is None


def test_cascading_refutation() -> None:
    # Deux faits faibles indépendants, chacun en conflit avec des faits solides.
    base = {
        parse_atom("est_un(x, a)"): a(Status.PROVED),
        parse_atom("est_un(y, a)"): a(Status.PROVED),
        parse_atom("disjoint(a, b)"): a(Status.PROVED),
        parse_atom("est_un(x, b)"): a(Status.UNVERIFIED),
        parse_atom("est_un(y, b)"): a(Status.UNVERIFIED),
    }
    state = revise(program_of(RULES), base)
    assert set(state.refuted) == {parse_atom("est_un(x, b)"), parse_atom("est_un(y, b)")}
    assert all(c.resolved for c in state.conflicts)
