"""Planner: decomposes a question from the macro level down to the nano level.

* MACRO  - the goal of the turn ("explain merge sort");
* MICRO  - the aspects worth covering (category, properties, examples...);
* ATOMIC - one knowledge-base query per aspect;
* NANO   - the epistemic check of every single retrieved fact (verifier).

Aspects are listed in a fixed order: the plan, hence the answer, is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from axiome.reasoning.terms import Atom, Literal, Var
from axiome.team.analyst import Analysis, Intent

X = Var("X")


class Scale(Enum):
    MACRO = "macro"
    MICRO = "micro"
    ATOMIC = "atomic"
    NANO = "nano"


class Aspect(Enum):
    CATEGORY = "category"
    PROPERTY = "property"
    MEMBERS = "members"
    UNIT = "unit"
    DIMENSION = "dimension"
    WORST_TIME = "worst_time"
    AVERAGE_TIME = "average_time"
    PREREQUISITE = "prerequisite"
    DISJOINT = "disjoint"
    WEB_DEFINITION = "web_definition"
    CHECK = "check"


def query_for(aspect: Aspect, subject: str, obj: str | None = None) -> Atom:
    if aspect is Aspect.CATEGORY:
        return Atom("is_a", (subject, X))
    if aspect is Aspect.PROPERTY:
        return Atom("has_property", (subject, X))
    if aspect is Aspect.MEMBERS:
        return Atom("is_a", (X, subject))
    if aspect is Aspect.UNIT:
        return Atom("si_unit", (subject, X))
    if aspect is Aspect.DIMENSION:
        return Atom("dimension", (subject, X))
    if aspect is Aspect.WORST_TIME:
        return Atom("worst_time_complexity", (subject, X))
    if aspect is Aspect.AVERAGE_TIME:
        return Atom("average_time_complexity", (subject, X))
    if aspect is Aspect.PREREQUISITE:
        return Atom("prerequisite", (subject, X))
    if aspect is Aspect.DISJOINT:
        return Atom("disjoint", (subject, X))
    if aspect is Aspect.WEB_DEFINITION:
        return Atom("defined_as", (subject, X))
    return Atom("is_a", (subject, obj or subject))


ASPECTS: dict[Intent, tuple[Aspect, ...]] = {
    Intent.DEFINITION: (
        Aspect.CATEGORY,
        Aspect.PROPERTY,
        Aspect.MEMBERS,
        Aspect.UNIT,
        Aspect.DIMENSION,
        Aspect.WORST_TIME,
        Aspect.AVERAGE_TIME,
        Aspect.PREREQUISITE,
        Aspect.DISJOINT,
        Aspect.WEB_DEFINITION,
    ),
    Intent.PROPERTIES: (Aspect.PROPERTY,),
    Intent.UNIT: (Aspect.UNIT, Aspect.DIMENSION),
    Intent.COMPLEXITY: (Aspect.WORST_TIME, Aspect.AVERAGE_TIME, Aspect.PREREQUISITE),
    Intent.MEMBERS: (Aspect.MEMBERS,),
    Intent.RESEARCH: (Aspect.WEB_DEFINITION,),
    Intent.CHECK_IS_A: (Aspect.CHECK,),
}


@dataclass(frozen=True, slots=True)
class Step:
    scale: Scale
    aspect: Aspect | None = None
    query: Literal | None = None


@dataclass(frozen=True, slots=True)
class Plan:
    intent: Intent
    subject: str
    steps: tuple[Step, ...]

    def atomic(self) -> list[Step]:
        return [s for s in self.steps if s.scale is Scale.ATOMIC]


def make_plan(analysis: Analysis) -> Plan | None:
    """A plan for a knowledge question, or None if the intent needs no lookup."""
    aspects = ASPECTS.get(analysis.intent)
    subject = analysis.subject.concept if analysis.subject else None
    if aspects is None or subject is None:
        return None
    obj = analysis.obj.concept if analysis.obj else None
    if analysis.intent is Intent.CHECK_IS_A and obj is None:
        return None
    steps = [Step(Scale.MACRO)]
    for aspect in aspects:
        steps.append(Step(Scale.MICRO, aspect))
        steps.append(Step(Scale.ATOMIC, aspect, Literal(query_for(aspect, subject, obj))))
    steps.append(Step(Scale.NANO))
    return Plan(analysis.intent, subject, tuple(steps))
