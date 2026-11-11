"""Verifier: attaches an epistemic status to every retrieved fact (nano level).

Checklist: never pass on a REFUTED fact as true, keep the reasons of each status,
and for web material only keep sentences actually present in a source.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from axiome.kernel import Kernel
from axiome.reasoning.terms import Atom
from axiome.team.planner import Aspect, Plan
from axiome.verification.epistemic import Assessment, Status


@dataclass(frozen=True, slots=True)
class Fact:
    atom: Atom
    assessment: Assessment
    base: bool  # stated directly rather than deduced

    @property
    def status(self) -> Status:
        return self.assessment.status


@dataclass(frozen=True, slots=True)
class Findings:
    facts: Mapping[Aspect, tuple[Fact, ...]]
    refuted: tuple[tuple[Atom, Assessment], ...] = ()

    def of(self, aspect: Aspect) -> tuple[Fact, ...]:
        return self.facts.get(aspect, ())

    def empty(self) -> bool:
        return not any(self.facts.values()) and not self.refuted


def verify(kernel: Kernel, plan: Plan) -> Findings:
    """Run the atomic queries of a plan and check every resulting fact."""
    state = kernel.state
    found: dict[Aspect, tuple[Fact, ...]] = {}
    refuted: list[tuple[Atom, Assessment]] = []
    for step in plan.atomic():
        assert step.aspect is not None and step.query is not None
        atom = step.query.atom
        if atom.is_ground() and atom in state.refuted:
            refuted.append((atom, state.refuted[atom]))
        facts = []
        for answer in state.model.query((step.query,)):
            fact = answer.premises[0]
            assessment = state.assessments[fact]
            if assessment.status is not Status.REFUTED:
                facts.append(Fact(fact, assessment, state.model.is_base(fact)))
        found[step.aspect] = tuple(facts)
    return Findings(found, tuple(refuted))


def ancestry(kernel: Kernel, concept: str, limit: int = 12) -> list[str]:
    """Taxonomy chain through direct (stated) parents: cat, mammal, vertebrate, animal."""
    model = kernel.state.model
    chain = [concept]
    while len(chain) <= limit:
        parents = sorted(
            str(f.args[1])
            for f in model.facts()
            if f.predicate == "is_a" and f.args[0] == chain[-1] and model.is_base(f)
        )
        nxt = next((p for p in parents if p not in chain), None)
        if nxt is None:
            break
        chain.append(nxt)
    return chain


def disjointness(
    kernel: Kernel, subject: str, obj: str
) -> tuple[str, str, tuple[Fact, ...]] | None:
    """Why ``subject`` cannot be an ``obj``: subject is an A, obj is a B, A and B are disjoint."""
    state = kernel.state
    model = state.model

    def classes(concept: str) -> list[tuple[str, Atom | None]]:
        out: list[tuple[str, Atom | None]] = [(concept, None)]
        for f in model.facts():
            if f.predicate == "is_a" and f.args[0] == concept:
                out.append((str(f.args[1]), f))
        return out

    for a, via_a in classes(subject):
        for b, via_b in classes(obj):
            clash = Atom("disjoint", (a, b))
            if clash in model:
                atoms = [x for x in (via_a, clash, via_b) if x is not None]
                facts = tuple(Fact(x, state.assessments[x], model.is_base(x)) for x in atoms)
                return a, b, facts
    return None
