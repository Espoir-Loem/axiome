"""Deterministic text rendering (no timestamps, no implicit ordering).

All display text comes from the locale catalogs; this module only lays it out.
"""

from __future__ import annotations

from axiome.i18n import t
from axiome.kernel import Explanation, QueryResult
from axiome.reasoning.engine import Proof
from axiome.reasoning.terms import format_term
from axiome.verification.epistemic import Assessment, Source
from axiome.verification.revision import BeliefState


def _tag(a: Assessment) -> str:
    return f"[{a.status.label}]"


def _bullets(a: Assessment, indent: str = "  ") -> list[str]:
    return [f"{indent}- {r}" for r in a.reasons]


def render_query(result: QueryResult) -> str:
    lines: list[str] = []
    for atom, a in result.refuted:
        lines.append(t("render.refuted_header", atom=atom, status=a.status.label))
        lines.extend(_bullets(a))
    if not result.answers:
        return "\n".join(lines) if lines else t("render.unknown")
    for view in result.answers:
        if view.answer.bindings:
            head = ", ".join(f"{v} = {format_term(term)}" for v, term in view.answer.bindings)
        else:
            head = t("render.yes")
        note = f"  {t('render.closed_world')}" if view.closed_world else ""
        lines.append(f"{head}  {_tag(view.overall)}{note}")
    count = len(result.answers)
    lines.append(t("render.answers_one" if count == 1 else "render.answers_many", count=count))
    return "\n".join(lines)


def _how(proof: Proof) -> str:
    if proof.rule is None:
        return t("render.how_base")
    if proof.rule.label:
        return t("render.how_rule", label=proof.rule.label)
    return t("render.how_rule_anonymous")


def render_proof(proof: Proof, ex: Explanation, indent: str = "") -> list[str]:
    out = [f"{indent}{proof.fact}  {_tag(ex.statuses[proof.fact])}  <- {_how(proof)}"]
    out.extend(f"{indent}  ∅ {absent}  {t('render.absent')}" for absent in proof.absent)
    for child in proof.children:
        out.extend(render_proof(child, ex, indent + "  "))
    return out


def render_explanation(ex: Explanation) -> str:
    lines = [f"{ex.fact}: {ex.assessment.status.label}", *_bullets(ex.assessment)]
    if ex.proof is not None:
        lines.append(t("render.proof_header"))
        lines.extend(render_proof(ex.proof, ex, "  "))
    return "\n".join(lines)


def render_conflicts(state: BeliefState) -> str:
    if not state.conflicts:
        return t("render.no_conflicts")
    lines: list[str] = []
    for c in state.conflicts:
        verdict = t("render.resolved" if c.resolved else "render.unresolved")
        lines.append(t("render.conflict_header", name=c.violation.constraint.name, verdict=verdict))
        lines.extend(f"  • {p}" for p in c.violation.premises)
        lines.append(t("render.weakest", facts=", ".join(map(str, c.culprits))))
    return "\n".join(lines)


def render_sources(sources: list[Source]) -> str:
    return "\n".join(
        t(
            "render.source_line",
            id=f"{s.id:<20}",
            kind=f"{s.kind.value:<12}",
            reliability=f"{s.reliability.name:<6}",
            name=s.name,
        )
        for s in sources
    )
