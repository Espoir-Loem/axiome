"""Statuts épistémiques : *pourquoi* croire une affirmation.

Spécification normative : ``docs/epistemologie.md``. Toute modification de ce
fichier doit être reflétée dans ce document (et inversement).

Le statut n'est PAS une probabilité : c'est le résultat de règles explicites,
ordonnées, appliquées sur des preuves typées. Deux exécutions sur les mêmes
preuves donnent toujours le même statut et les mêmes raisons.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    """Du plus faible au plus fort. La valeur sert à comparer."""

    REFUTED = 0
    CONTESTED = 1
    UNVERIFIED = 2
    PLAUSIBLE = 3
    CONFIRMED = 4
    VERIFIED = 5
    PROVED = 6

    @property
    def label(self) -> str:
        return _LABELS[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Status):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Status):
            return NotImplemented
        return self.value <= other.value


_LABELS = {
    Status.REFUTED: "RÉFUTÉ",
    Status.CONTESTED: "CONTESTÉ",
    Status.UNVERIFIED: "NON VÉRIFIÉ",
    Status.PLAUSIBLE: "PLAUSIBLE",
    Status.CONFIRMED: "CONFIRMÉ",
    Status.VERIFIED: "VÉRIFIÉ",
    Status.PROVED: "PROUVÉ",
}


class SourceKind(Enum):
    AXIOM = "axiome"  # définition ou connaissance de référence curée par le projet
    PROOF = "preuve"  # démonstration logique/mathématique
    COMPUTATION = "calcul"  # calcul ou exécution reproductible
    REFERENCE = "reference"  # encyclopédie, base de données de référence
    PUBLICATION = "publication"  # article scientifique
    USER = "utilisateur"
    OTHER = "autre"


DECISIVE_SUPPORT = {SourceKind.AXIOM: Status.PROVED, SourceKind.PROOF: Status.PROVED}
DECISIVE = frozenset({SourceKind.AXIOM, SourceKind.PROOF, SourceKind.COMPUTATION})


class Reliability(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class Stance(Enum):
    SUPPORTS = "soutient"
    CONTRADICTS = "contredit"


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    name: str
    kind: SourceKind
    reliability: Reliability
    organization: str  # deux sources de la même organisation ne sont pas indépendantes
    url: str = ""


@dataclass(frozen=True, slots=True)
class Evidence:
    source: Source
    stance: Stance
    excerpt: str = ""


@dataclass(frozen=True, slots=True)
class Assessment:
    status: Status
    reasons: tuple[str, ...]


def _orgs(evidence: Sequence[Evidence], minimum: Reliability) -> list[str]:
    return sorted(
        {e.source.organization for e in evidence if e.source.reliability.value >= minimum.value}
    )


def assess(evidence: Sequence[Evidence]) -> Assessment:
    """Applique les règles E1…E8 de ``docs/epistemologie.md`` dans l'ordre."""
    ordered = sorted(evidence, key=lambda e: (e.stance.value, e.source.id))
    pro = [e for e in ordered if e.stance is Stance.SUPPORTS]
    con = [e for e in ordered if e.stance is Stance.CONTRADICTS]

    decisive_con = [e for e in con if e.source.kind in DECISIVE]
    if decisive_con:  # E1
        return Assessment(
            Status.REFUTED, tuple(f"contredit par {e.source.name}" for e in decisive_con)
        )
    for kind, status in DECISIVE_SUPPORT.items():  # E2
        hits = [e for e in pro if e.source.kind is kind]
        if hits:
            return Assessment(status, tuple(f"établi par {e.source.name}" for e in hits))
    computed = [e for e in pro if e.source.kind is SourceKind.COMPUTATION]
    if computed:  # E3
        return Assessment(Status.VERIFIED, tuple(f"vérifié par {e.source.name}" for e in computed))

    pro_high, con_high = _orgs(pro, Reliability.HIGH), _orgs(con, Reliability.HIGH)
    if con_high and pro:  # E4
        return Assessment(
            Status.CONTESTED,
            (
                f"soutenu par {', '.join(_orgs(pro, Reliability.LOW))}",
                f"contredit par {', '.join(con_high)}",
            ),
        )
    if len(con_high) >= 2:  # E5
        return Assessment(
            Status.REFUTED,
            (f"contredit par des sources fiables indépendantes : {', '.join(con_high)}",),
        )
    if len(pro_high) >= 2:  # E6
        return Assessment(
            Status.CONFIRMED,
            (f"confirmé par des sources fiables indépendantes : {', '.join(pro_high)}",),
        )
    if pro_high or len(_orgs(pro, Reliability.MEDIUM)) >= 2:  # E7
        names = ", ".join(_orgs(pro, Reliability.MEDIUM))
        return Assessment(
            Status.PLAUSIBLE, (f"une seule source fiable ou plusieurs moyennes : {names}",)
        )
    if con:  # E8
        reason = "contredit par " + ", ".join(_orgs(con, Reliability.LOW))
        status = Status.CONTESTED if pro else Status.UNVERIFIED
        return Assessment(status, (reason,))
    if pro:
        return Assessment(
            Status.UNVERIFIED, (f"seulement affirmé par {', '.join(_orgs(pro, Reliability.LOW))}",)
        )
    return Assessment(Status.UNVERIFIED, ("aucune preuve enregistrée",))
