"""Events streamed by a conversation turn.

A turn is a generator of events, so an interface can show the first words
immediately and the rest as it is produced. All text is already rendered in the
session language.
"""

from __future__ import annotations

from dataclasses import dataclass

from axiome.verification.epistemic import Source, Status


@dataclass(frozen=True, slots=True)
class Thinking:
    """What the team is doing right now (shown discreetly)."""

    text: str


@dataclass(frozen=True, slots=True)
class Searching:
    provider: str
    query: str


@dataclass(frozen=True, slots=True)
class SourceFound:
    source: Source


@dataclass(frozen=True, slots=True)
class Say:
    """One approved sentence of the answer."""

    text: str
    status: Status | None = None  # None for conversational (non-factual) sentences
    support: tuple[str, ...] = ()  # facts or source ids backing the sentence
    role: str = "lead"  # layout: lead, point, note, see_also, source, social


@dataclass(frozen=True, slots=True)
class Done:
    approved: int
    blocked: int  # sentences stopped by the reviewer
    corrected: int  # sentences rewritten by the style gate


Event = Thinking | Searching | SourceFound | Say | Done
