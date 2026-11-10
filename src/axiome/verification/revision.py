"""Belief revision: combining logic with epistemic statuses.

Algorithm (``docs/epistemologie.md`` section 3):

1. base facts REFUTED by their own evidence are excluded;
2. the program is saturated over the remaining facts;
3. a derived fact's status is the weakest link of its canonical proof
   (premises + rule; a hypothetical rule caps it at UNVERIFIED, reasoning from
   an absence caps it at PLAUSIBLE);
4. for each constraint violation, trace back to the supporting base facts. If
   there is a **unique** weakest one and all others are at least CONFIRMED, it is
   REFUTED and we restart at step 1. Otherwise the weakest ones become CONTESTED
   and the conflict is reported as unresolved.

Each round removes at least one fact, so the loop terminates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from axiome.i18n import Msg, msg
from axiome.reasoning.engine import Model, Violation, evaluate
from axiome.reasoning.program import Program
from axiome.reasoning.terms import Atom
from axiome.verification.epistemic import Assessment, Status

HYPOTHESIS_CAP = Status.UNVERIFIED
# A conclusion drawn from the ABSENCE of a fact (negation as failure) is never
# demonstrated: it only holds if the knowledge base is complete on that point.
CLOSED_WORLD_CAP = Status.PLAUSIBLE
MAX_LISTED_FACTS = 8


@dataclass(frozen=True, slots=True)
class Conflict:
    violation: Violation
    culprits: tuple[Atom, ...]  # weakest supporting base facts
    resolved: bool  # True if a culprit was refuted


@dataclass(frozen=True)
class BeliefState:
    model: Model
    assessments: Mapping[Atom, Assessment]  # every established fact of the model
    refuted: Mapping[Atom, Assessment]  # discarded base facts
    conflicts: tuple[Conflict, ...]

    def status(self, atom: Atom) -> Assessment | None:
        return self.assessments.get(atom) or self.refuted.get(atom)


def _derived_assessments(model: Model, base: Mapping[Atom, Assessment]) -> dict[Atom, Assessment]:
    out: dict[Atom, Assessment] = {}

    def visit(atom: Atom) -> Assessment:
        if atom in out:
            return out[atom]
        just = model.justification(atom)
        if just.rule_index is None:
            result = base[atom]
        else:
            rule = model.program.rules[just.rule_index]
            weakest = min((visit(p).status for p in just.premises), default=Status.PROVED)
            label = rule.label or just.rule_index + 1
            reasons: list[Msg] = [msg("reason.derived_by_rule", rule=label)]
            if not rule.axiomatic and weakest > HYPOTHESIS_CAP:
                weakest = HYPOTHESIS_CAP
                reasons.append(msg("reason.hypothesis_rule"))
            if just.absent and weakest > CLOSED_WORLD_CAP:
                weakest = CLOSED_WORLD_CAP
                absent = ", ".join(map(str, just.absent))
                reasons.append(msg("reason.relies_on_absence", atoms=absent))
            result = Assessment(weakest, (*reasons, msg("reason.weakest_link")))
        out[atom] = result
        return result

    for atom in model.facts():
        visit(atom)
    return out


def _roots(v: Violation, model: Model) -> frozenset[Atom]:
    return frozenset().union(*(model.support(p) for p in v.premises))


def _judge(
    v: Violation, model: Model, effective: Mapping[Atom, Assessment]
) -> tuple[Conflict, tuple[Atom, Assessment] | None]:
    """Decide one violation: refute a unique weakest culprit, or contest them all."""
    roots = sorted(_roots(v, model), key=Atom.sort_key)
    weakest = min(effective[r].status for r in roots)
    culprits = tuple(r for r in roots if effective[r].status == weakest)
    others = [effective[r].status for r in roots if r not in culprits]
    if len(culprits) == 1 and others and min(others) >= Status.CONFIRMED:
        culprit = culprits[0]
        kept = [str(r) for r in roots if r != culprit][:MAX_LISTED_FACTS]
        verdict = Assessment(
            Status.REFUTED,
            (
                msg("reason.violates_constraint", name=v.constraint.name),
                msg("reason.incompatible_with", facts=", ".join(kept)),
            ),
        )
        return Conflict(v, culprits, resolved=True), (culprit, verdict)
    return Conflict(v, culprits, resolved=False), None


def _contest(conflicts: list[Conflict], effective: dict[Atom, Assessment]) -> None:
    for c in conflicts:
        for atom in c.culprits:
            if effective[atom].status > Status.CONTESTED:
                reason = msg("reason.in_conflict", name=c.violation.constraint.name)
                effective[atom] = Assessment(Status.CONTESTED, (reason, *effective[atom].reasons))


def revise(program: Program, base: Mapping[Atom, Assessment]) -> BeliefState:
    refuted = {a: s for a, s in base.items() if s.status is Status.REFUTED}
    history: list[Conflict] = []  # conflicts resolved in earlier rounds
    while True:
        active = {a: s for a, s in base.items() if a not in refuted}
        model = evaluate(program, active)
        effective = dict(active)
        conflicts: list[Conflict] = []
        newly_refuted: dict[Atom, Assessment] = {}
        seen: set[tuple[str, frozenset[Atom]]] = set()
        for v in model.violations:
            key = (v.constraint.name, _roots(v, model))
            if key in seen:  # e.g. symmetric disjointness yields twin violations
                continue
            seen.add(key)
            conflict, refutation = _judge(v, model, effective)
            conflicts.append(conflict)
            if refutation is not None:
                newly_refuted[refutation[0]] = refutation[1]

        if newly_refuted:
            refuted.update(newly_refuted)
            history.extend(c for c in conflicts if c.resolved)
            continue

        _contest(conflicts, effective)
        assessments = _derived_assessments(model, effective)
        return BeliefState(model, assessments, refuted, (*history, *conflicts))
