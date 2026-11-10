"""Rendu textuel déterministe (aucun horodatage, aucun ordre implicite)."""

from __future__ import annotations

from axiome.kernel import Explanation, QueryResult
from axiome.reasoning.engine import Proof
from axiome.reasoning.terms import format_term
from axiome.verification.epistemic import Assessment, Source
from axiome.verification.revision import BeliefState

UNKNOWN = (
    "Je ne sais pas : rien dans ma base ne permet de l'établir.\n"
    "(Absence de preuve ≠ preuve d'absence : je ne conclus pas que c'est faux.)"
)


def _tag(a: Assessment) -> str:
    return f"[{a.status.label}]"


def render_query(result: QueryResult) -> str:
    lines: list[str] = []
    for atom, a in result.refuted:
        lines.append(f"Non. {atom} est {a.status.label} :")
        lines.extend(f"  - {r}" for r in a.reasons)
    if not result.answers:
        return "\n".join(lines) if lines else UNKNOWN
    for view in result.answers:
        weakest = view.overall
        if view.answer.bindings:
            head = ", ".join(f"{v} = {format_term(t)}" for v, t in view.answer.bindings)
        else:
            head = "Oui"
        note = "  (monde clos)" if view.closed_world else ""
        lines.append(f"{head}  {_tag(weakest)}{note}")
    lines.append(f"({len(result.answers)} réponse{'s' if len(result.answers) > 1 else ''})")
    return "\n".join(lines)


def render_proof(proof: Proof, ex: Explanation, indent: str = "") -> list[str]:
    a = ex.statuses[proof.fact]
    how = (
        f"règle {proof.rule.label}"
        if proof.rule and proof.rule.label
        else ("règle" if proof.rule else "fait de base")
    )
    out = [f"{indent}{proof.fact}  {_tag(a)}  ← {how}"]
    for absent in proof.absent:
        out.append(f"{indent}  ∅ {absent}  (absent de la base)")
    for child in proof.children:
        out.extend(render_proof(child, ex, indent + "  "))
    return out


def render_explanation(ex: Explanation) -> str:
    lines = [f"{ex.fact} : {ex.assessment.status.label}"]
    lines.extend(f"  - {r}" for r in ex.assessment.reasons)
    if ex.proof is not None:
        lines.append("Preuve :")
        lines.extend(render_proof(ex.proof, ex, "  "))
    return "\n".join(lines)


def render_conflicts(state: BeliefState) -> str:
    if not state.conflicts:
        return "Aucune contradiction détectée."
    lines: list[str] = []
    for c in state.conflicts:
        verdict = "résolu (réfuté)" if c.resolved else "non résolu (contesté)"
        lines.append(f"Contrainte « {c.violation.constraint.name} » — {verdict}")
        lines.extend(f"  • {p}" for p in c.violation.premises)
        lines.append("  maillon(s) le(s) plus faible(s) : " + ", ".join(map(str, c.culprits)))
    return "\n".join(lines)


def render_sources(sources: list[Source]) -> str:
    return "\n".join(
        f"{s.id:<20} {s.kind.value:<12} fiabilité={s.reliability.name:<6} {s.name}" for s in sources
    )
