"""Rules, integrity constraints and logic program validation.

A :class:`Program` can only be built if it is **safe** (every variable of the
head or of a negated literal occurs in a positive body literal) and
**stratifiable** (no recursion through negation). Together these guarantee a
unique, computable model: the foundation of determinism.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from axiome.core.errors import ProgramError
from axiome.i18n import Msg, msg
from axiome.reasoning.terms import Atom, Literal, Var


@dataclass(frozen=True, slots=True)
class Rule:
    """``head :- body``. ``axiomatic`` = reference rule (as opposed to a hypothesis)."""

    head: Atom
    body: tuple[Literal, ...]
    label: str = ""
    axiomatic: bool = True

    def __str__(self) -> str:
        prefix = f"[{self.label}] " if self.label else ""
        return f"{prefix}{self.head} :- {', '.join(map(str, self.body))}."


@dataclass(frozen=True, slots=True)
class Constraint:
    """Integrity constraint: its body must NEVER be satisfied."""

    name: str
    body: tuple[Literal, ...]

    def __str__(self) -> str:
        return f"! {self.name} :- {', '.join(map(str, self.body))}."


def check_body_safety(body: Sequence[Literal], required: Sequence[Var], where: Msg) -> None:
    """Check that ``required`` and negated variables are bound by a positive literal."""
    positives = [lit for lit in body if not lit.negated]
    if not positives:
        raise ProgramError("program.no_positive_literal", where=where)
    bound = {v for lit in positives for v in lit.atom.variables()}
    for v in required:
        if v not in bound:
            raise ProgramError("program.unbound_variable", where=where, var=v)
    for lit in body:
        if lit.negated:
            for v in lit.atom.variables():
                if v not in bound:
                    raise ProgramError("program.negated_only", where=where, var=v)


def _stratify(rules: Sequence[Rule]) -> dict[str, int]:
    """Assign a stratum to each predicate (classic fixpoint algorithm)."""
    preds = sorted(
        {r.head.predicate for r in rules} | {lit.atom.predicate for r in rules for lit in r.body}
    )
    stratum = dict.fromkeys(preds, 0)
    limit = len(preds)
    changed = True
    while changed:
        changed = False
        for r in rules:
            h = r.head.predicate
            for lit in r.body:
                need = stratum[lit.atom.predicate] + (1 if lit.negated else 0)
                if stratum[h] < need:
                    if need > limit:
                        raise ProgramError(
                            "program.not_stratifiable", head=h, dependency=lit.atom.predicate
                        )
                    stratum[h] = need
                    changed = True
    return stratum


@dataclass(frozen=True)
class Program:
    rules: tuple[Rule, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    strata: tuple[tuple[int, ...], ...] = field(init=False)

    def __post_init__(self) -> None:
        for i, r in enumerate(self.rules):
            if any(lit.atom.predicate == r.head.predicate and lit.negated for lit in r.body):
                raise ProgramError("program.negates_own_head", index=i + 1)
            check_body_safety(r.body, r.head.variables(), msg("where.rule", rule=r))
        for c in self.constraints:
            check_body_safety(c.body, (), msg("where.constraint", name=c.name))
        levels = _stratify(self.rules)
        groups: dict[int, list[int]] = {}
        for i, r in enumerate(self.rules):
            groups.setdefault(levels[r.head.predicate], []).append(i)
        object.__setattr__(self, "strata", tuple(tuple(groups[k]) for k in sorted(groups)))
