"""Règles, contraintes d'intégrité et validation d'un programme logique.

Un :class:`Program` n'est construit que s'il est **sûr** (toute variable de la tête
ou d'un littéral nié apparaît dans un littéral positif du corps) et
**stratifiable** (aucune récursion à travers une négation). Ces deux propriétés
garantissent un modèle unique et calculable : c'est le socle du déterminisme.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from axiome.core.errors import ProgramError
from axiome.reasoning.terms import Atom, Literal, Var


@dataclass(frozen=True, slots=True)
class Rule:
    """``tête :- corps``. ``axiomatic`` = règle de la base de référence (vs hypothèse)."""

    head: Atom
    body: tuple[Literal, ...]
    label: str = ""
    axiomatic: bool = True

    def __str__(self) -> str:
        prefix = f"[{self.label}] " if self.label else ""
        return f"{prefix}{self.head} :- {', '.join(map(str, self.body))}."


@dataclass(frozen=True, slots=True)
class Constraint:
    """Contrainte d'intégrité : le corps ne doit JAMAIS être satisfait."""

    name: str
    body: tuple[Literal, ...]

    def __str__(self) -> str:
        return f"! {self.name} :- {', '.join(map(str, self.body))}."


def check_body_safety(body: Sequence[Literal], required: Sequence[Var], where: str) -> None:
    """Vérifie que ``required`` et les variables niées sont liées par un littéral positif."""
    positives = [lit for lit in body if not lit.negated]
    if not positives:
        raise ProgramError(f"{where} : le corps doit contenir au moins un littéral positif")
    bound = {v for lit in positives for v in lit.atom.variables()}
    for v in required:
        if v not in bound:
            raise ProgramError(f"{where} : la variable {v} n'est liée par aucun littéral positif")
    for lit in body:
        if lit.negated:
            for v in lit.atom.variables():
                if v not in bound:
                    raise ProgramError(f"{where} : la variable {v} n'apparaît que sous négation")


def _stratify(rules: Sequence[Rule]) -> dict[str, int]:
    """Attribue une strate à chaque prédicat (algorithme de point fixe classique)."""
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
                            f"programme non stratifiable : « {h} » dépend récursivement "
                            f"de la négation de « {lit.atom.predicate} »"
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
                raise ProgramError(f"règle {i + 1} : un prédicat ne peut pas nier sa propre tête")
            check_body_safety(r.body, r.head.variables(), f"règle « {r} »")
        for c in self.constraints:
            check_body_safety(c.body, (), f"contrainte « {c.name} »")
        levels = _stratify(self.rules)
        groups: dict[int, list[int]] = {}
        for i, r in enumerate(self.rules):
            groups.setdefault(levels[r.head.predicate], []).append(i)
        object.__setattr__(self, "strata", tuple(tuple(groups[k]) for k in sorted(groups)))
