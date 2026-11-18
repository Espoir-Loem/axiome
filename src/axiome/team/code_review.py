"""Bridge between code diagnostics and the conversation's Reviewer (M7.1).

Code facts are facts like any other: each diagnostic becomes a factual claim
supported by its atoms, at status ``VERIFIED`` (E3: a reproducible
computation), and goes through the same R1-R3 and style gate as the rest of
the answers. The code package itself never imports the team (RFC-0002).
"""

from __future__ import annotations

from collections.abc import Iterable

from axiome.code.analyze import Diagnostic
from axiome.i18n import t
from axiome.language.pack import LanguagePack
from axiome.team.reviewer import Review, Reviewer
from axiome.team.writer import POINT, Claim
from axiome.verification.epistemic import Status


def finding_text(diagnostic: Diagnostic) -> str:
    """One sentence: severity, message, position and cited line."""
    severity = t(f"code.severity.{diagnostic.severity}")
    return t(
        "code.finding",
        severity=severity,
        message=diagnostic.message,
        position=diagnostic.position,
        line=diagnostic.line,
    )


def claims_for(diagnostics: Iterable[Diagnostic]) -> list[Claim]:
    """Every diagnostic becomes one supported, located claim."""
    return [
        Claim(
            finding_text(diagnostic),
            Status.VERIFIED,
            tuple(str(atom) for atom in diagnostic.support),
            role=POINT,
        )
        for diagnostic in diagnostics
    ]


def review_findings(
    diagnostics: Iterable[Diagnostic],
    pack: LanguagePack,
    waivers: frozenset[str] = frozenset(),
) -> Review:
    """Run the existing Reviewer over code findings (nothing special-cased)."""
    return Reviewer(pack).review(claims_for(diagnostics), waivers)
