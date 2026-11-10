"""Révision des croyances : combiner logique et statuts épistémiques.

Algorithme (``docs/epistemologie.md`` §3) :

1. les faits de base RÉFUTÉS par leurs preuves sont exclus ;
2. on sature le programme sur les faits restants ;
3. le statut d'un fait dérivé = maillon le plus faible de sa preuve canonique
   (prémisses + règle ; une règle hypothétique plafonne à NON VÉRIFIÉ) ;
4. pour chaque violation de contrainte, on remonte aux faits de base qui la
   supportent. S'il existe un **unique** maillon le plus faible et que tous les
   autres sont au moins CONFIRMÉS, il est RÉFUTÉ et on recommence en 1.
   Sinon, les maillons les plus faibles deviennent CONTESTÉS (conflit signalé).

Chaque tour retire au moins un fait : la boucle termine.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from axiome.reasoning.engine import Model, Violation, evaluate
from axiome.reasoning.program import Program
from axiome.reasoning.terms import Atom
from axiome.verification.epistemic import Assessment, Status

HYPOTHESIS_CAP = Status.UNVERIFIED
# Une conclusion tirée de l'ABSENCE d'un fait (négation par l'échec) n'est jamais
# démontrée : elle n'est valable que si la base est complète sur ce point.
CLOSED_WORLD_CAP = Status.PLAUSIBLE


@dataclass(frozen=True, slots=True)
class Conflict:
    violation: Violation
    culprits: tuple[Atom, ...]  # faits de base les plus faibles
    resolved: bool  # True si un coupable a été réfuté


@dataclass(frozen=True)
class BeliefState:
    model: Model
    assessments: Mapping[Atom, Assessment]  # tous les faits établis du modèle
    refuted: Mapping[Atom, Assessment]  # faits de base écartés
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
            parts = [visit(p) for p in just.premises]
            weakest = min((a.status for a in parts), default=Status.PROVED)
            reasons = [f"déduit par la règle {rule.label or just.rule_index + 1}"]
            if not rule.axiomatic and weakest > HYPOTHESIS_CAP:
                weakest = HYPOTHESIS_CAP
                reasons.append("la règle utilisée est une hypothèse")
            if just.absent and weakest > CLOSED_WORLD_CAP:
                weakest = CLOSED_WORLD_CAP
                missing = ", ".join(map(str, just.absent))
                reasons.append(f"repose sur l'absence de : {missing} (hypothèse du monde clos)")
            result = Assessment(weakest, (*reasons, "maillon le plus faible de la preuve"))
        out[atom] = result
        return result

    for atom in model.facts():
        visit(atom)
    return out


def revise(program: Program, base: Mapping[Atom, Assessment]) -> BeliefState:
    refuted: dict[Atom, Assessment] = {a: s for a, s in base.items() if s.status is Status.REFUTED}
    history: list[Conflict] = []  # conflits résolus lors des tours précédents
    while True:
        active = {a: s for a, s in base.items() if a not in refuted}
        model = evaluate(program, active)
        effective = dict(active)
        conflicts: list[Conflict] = []
        newly_refuted: dict[Atom, Assessment] = {}

        seen_roots: set[tuple[str, frozenset[Atom]]] = set()
        for v in model.violations:
            root_set = frozenset().union(*(model.support(p) for p in v.premises))
            if (v.constraint.name, root_set) in seen_roots:  # ex. symétrie de disjoint
                continue
            seen_roots.add((v.constraint.name, root_set))
            roots = sorted(root_set, key=Atom.sort_key)
            weakest = min(effective[r].status for r in roots)
            culprits = tuple(r for r in roots if effective[r].status == weakest)
            others = [effective[r].status for r in roots if r not in culprits]
            if len(culprits) == 1 and others and min(others) >= Status.CONFIRMED:
                newly_refuted[culprits[0]] = Assessment(
                    Status.REFUTED,
                    (
                        f"viole la contrainte « {v.constraint.name} »",
                        "incompatible avec : "
                        + ", ".join(str(r) for r in roots[:8] if r != culprits[0]),
                    ),
                )
                conflicts.append(Conflict(v, culprits, resolved=True))
            else:
                conflicts.append(Conflict(v, culprits, resolved=False))

        if newly_refuted:
            refuted.update(newly_refuted)
            history.extend(c for c in conflicts if c.resolved)
            continue

        for c in conflicts:
            for atom in c.culprits:
                if effective[atom].status > Status.CONTESTED:
                    effective[atom] = Assessment(
                        Status.CONTESTED,
                        (
                            f"en conflit (contrainte « {c.violation.constraint.name} »)",
                            *effective[atom].reasons,
                        ),
                    )
        return BeliefState(
            model, _derived_assessments(model, effective), refuted, (*history, *conflicts)
        )
