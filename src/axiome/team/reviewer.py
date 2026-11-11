"""Reviewer: the quality gate. Nothing reaches the user without passing it.

Zero-error rules (a failing sentence is blocked, never "fixed" by guessing):

R1  a factual sentence must cite at least one fact or source;
R2  a fact below CONFIRMED must say so in the sentence (hedge);
R3  a refuted fact is only ever stated as refuted.

Style gate (``docs/signes-ia.md``): AI tells are removed deterministically; an
assistant self-reference (S2) blocks the sentence. A category is skipped when the
user explicitly asked for it in this turn (waiver).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from axiome.language.pack import LanguagePack
from axiome.perception.normalize import fold
from axiome.team.writer import Claim
from axiome.verification.epistemic import Status

BLOCKING_CATEGORY = "S2"
TYPOGRAPHY_CATEGORY = "S5"
_EMOJI = re.compile(
    "[\U0001f000-\U0001faff☀-➿⬀-⯿️‍⃣]",
)
_DASH = re.compile(r"\s*[—–]\s*|\s+[→⇒➡]\s+|[→⇒➡]")
_MARKUP = re.compile(r"\*\*|__|^#+\s*", re.MULTILINE)
_SPACES = re.compile(r"\s{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.])")


@dataclass
class Review:
    approved: list[Claim] = field(default_factory=list)
    blocked: list[tuple[Claim, str]] = field(default_factory=list)  # (claim, rule)
    corrected: int = 0


def _typography(text: str) -> str:
    text = _EMOJI.sub("", text)
    text = _DASH.sub(", ", text)
    return _MARKUP.sub("", text)


def _tidy(text: str) -> str:
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", _SPACES.sub(" ", text)).strip(" ,")
    return text[:1].upper() + text[1:]


class Reviewer:
    def __init__(self, pack: LanguagePack) -> None:
        self.pack = pack

    def style(
        self, text: str, waivers: frozenset[str] = frozenset()
    ) -> tuple[str | None, list[str]]:
        """Return (cleaned text or None if blocked, categories that fired)."""
        fired: list[str] = []
        if TYPOGRAPHY_CATEGORY not in waivers:
            cleaned = _typography(text)
            if cleaned != text:
                fired.append(TYPOGRAPHY_CATEGORY)
                text = cleaned
        for category, patterns in self.pack.style.rules:
            if category in waivers:
                continue
            for pattern in patterns:
                folded = fold(text)
                spans = [m.span() for m in pattern.finditer(folded)]
                if not spans:
                    continue
                fired.append(category)
                if category == BLOCKING_CATEGORY:
                    return None, fired
                for start, end in reversed(spans):
                    text = text[:start] + text[end:]
        return (_tidy(text) if fired else text), sorted(set(fired))

    @staticmethod
    def substance(claim: Claim) -> str | None:
        """The violated zero-error rule, if any."""
        if not claim.factual:
            return None
        if not claim.support:
            return "R1"
        if claim.status is Status.REFUTED and not claim.hedged:
            return "R3"
        if claim.status is not None and claim.status < Status.CONFIRMED and not claim.hedged:
            return "R2"
        return None

    def review(self, claims: Iterable[Claim], waivers: frozenset[str] = frozenset()) -> Review:
        out = Review()
        for claim in claims:
            rule = self.substance(claim)
            if rule is not None:
                out.blocked.append((claim, rule))
                continue
            text, fired = self.style(claim.text, waivers)
            if text is None:
                out.blocked.append((claim, BLOCKING_CATEGORY))
                continue
            if not text.strip(" .,!?"):
                out.blocked.append((claim, "empty"))
                continue
            out.corrected += bool(fired)
            out.approved.append(replace(claim, text=text) if fired else claim)
        return out
