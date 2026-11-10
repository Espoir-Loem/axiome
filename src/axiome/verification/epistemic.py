"""Epistemic statuses: *why* a claim deserves belief.

Normative specification: ``docs/epistemologie.md``. Any change to this file must
be reflected there (and vice versa).

A status is NOT a probability: it is the outcome of explicit, ordered rules
applied to typed evidence. Two runs on the same evidence always produce the same
status and the same reasons.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from axiome.i18n import Msg, msg, t


class Status(Enum):
    """From weakest to strongest; the value is used for comparisons."""

    REFUTED = 0
    CONTESTED = 1
    UNVERIFIED = 2
    PLAUSIBLE = 3
    CONFIRMED = 4
    VERIFIED = 5
    PROVED = 6

    @property
    def label(self) -> str:
        return t(f"status.{self.name}")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Status):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Status):
            return NotImplemented
        return self.value <= other.value


class SourceKind(Enum):
    AXIOM = "axiom"  # definition or reference knowledge curated by the project
    PROOF = "proof"  # logical or mathematical demonstration
    COMPUTATION = "computation"  # reproducible computation or execution
    REFERENCE = "reference"  # encyclopedia, reference database
    PUBLICATION = "publication"  # scientific paper
    USER = "user"
    OTHER = "other"


DECISIVE = frozenset({SourceKind.AXIOM, SourceKind.PROOF, SourceKind.COMPUTATION})


class Reliability(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class Stance(Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    name: str
    kind: SourceKind
    reliability: Reliability
    organization: str  # two sources from the same organization are not independent
    url: str = ""


@dataclass(frozen=True, slots=True)
class Evidence:
    source: Source
    stance: Stance
    excerpt: str = ""


@dataclass(frozen=True, slots=True)
class Assessment:
    status: Status
    reasons: tuple[Msg, ...]


def _orgs(evidence: Sequence[Evidence], minimum: Reliability) -> str:
    """Comma-separated, sorted, de-duplicated organizations at or above ``minimum``."""
    return ", ".join(
        sorted(
            {e.source.organization for e in evidence if e.source.reliability.value >= minimum.value}
        )
    )


def _count(evidence: Sequence[Evidence], minimum: Reliability) -> int:
    return len(
        {e.source.organization for e in evidence if e.source.reliability.value >= minimum.value}
    )


def _names(evidence: Sequence[Evidence]) -> str:
    return ", ".join(e.source.name for e in evidence)


def assess(evidence: Sequence[Evidence]) -> Assessment:
    """Apply rules E1-E8 of ``docs/epistemologie.md`` in order."""
    ordered = sorted(evidence, key=lambda e: (e.stance.value, e.source.id))
    pro = [e for e in ordered if e.stance is Stance.SUPPORTS]
    con = [e for e in ordered if e.stance is Stance.CONTRADICTS]
    high = Reliability.HIGH

    decisive_con = [e for e in con if e.source.kind in DECISIVE]
    if decisive_con:  # E1
        return Assessment(
            Status.REFUTED, (msg("reason.contradicted_by", sources=_names(decisive_con)),)
        )
    proved = [e for e in pro if e.source.kind in (SourceKind.AXIOM, SourceKind.PROOF)]
    if proved:  # E2
        return Assessment(Status.PROVED, (msg("reason.established_by", sources=_names(proved)),))
    computed = [e for e in pro if e.source.kind is SourceKind.COMPUTATION]
    if computed:  # E3
        return Assessment(Status.VERIFIED, (msg("reason.verified_by", sources=_names(computed)),))

    if _count(con, high) and pro:  # E4
        return Assessment(
            Status.CONTESTED,
            (
                msg("reason.supported_by", sources=_orgs(pro, Reliability.LOW)),
                msg("reason.contradicted_by", sources=_orgs(con, high)),
            ),
        )
    if _count(con, high) >= 2:  # E5
        return Assessment(
            Status.REFUTED, (msg("reason.refuted_independent", sources=_orgs(con, high)),)
        )
    if _count(pro, high) >= 2:  # E6
        return Assessment(
            Status.CONFIRMED, (msg("reason.confirmed_independent", sources=_orgs(pro, high)),)
        )
    if _count(pro, high) or _count(pro, Reliability.MEDIUM) >= 2:  # E7
        return Assessment(
            Status.PLAUSIBLE,
            (msg("reason.single_reliable", sources=_orgs(pro, Reliability.MEDIUM)),),
        )
    if con:  # E8
        reason = msg("reason.contradicted_by", sources=_orgs(con, Reliability.LOW))
        return Assessment(Status.CONTESTED if pro else Status.UNVERIFIED, (reason,))
    if pro:
        return Assessment(
            Status.UNVERIFIED,
            (msg("reason.only_asserted_by", sources=_orgs(pro, Reliability.LOW)),),
        )
    return Assessment(Status.UNVERIFIED, (msg("reason.no_evidence"),))
