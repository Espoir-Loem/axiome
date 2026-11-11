"""Adaptive level: beginner, intermediate or expert, tracked per domain.

The same verified content is written differently for each level; only the form
changes, never the truth of what is said. Signals (all deterministic):

* explicit request ("explique simplement", "expert level") sets the level;
* "I did not understand" lowers it by one step;
* using at least two technical terms of a domain raises it by one step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum

from axiome.knowledge.store import KnowledgeStore
from axiome.language.lexicon import Lexicon
from axiome.perception.normalize import fold, words

ANY_DOMAIN = "*"
META_PREFIX = "level:"
RAISE_THRESHOLD = 2  # technical terms in one message that reveal familiarity


class Level(IntEnum):
    BEGINNER = 0
    INTERMEDIATE = 1
    EXPERT = 2


DEFAULT_LEVEL = Level.INTERMEDIATE


class LevelProfile:
    """Per-domain levels, persisted in the store's ``meta`` table when one is given."""

    def __init__(self, store: KnowledgeStore | None = None) -> None:
        self._store = store
        self._levels: dict[str, Level] = {}
        if store is not None:
            for key, value in store.meta_items(META_PREFIX):
                self._levels[key.removeprefix(META_PREFIX)] = Level(int(value))

    def level(self, domain: str) -> Level:
        for key in (domain, ANY_DOMAIN):
            if key in self._levels:
                return self._levels[key]
        return DEFAULT_LEVEL

    def set(self, domain: str, level: Level) -> None:
        self._levels[domain] = level
        if self._store is not None:
            self._store.set_meta(META_PREFIX + domain, str(int(level)))

    def lower(self, domain: str) -> Level:
        level = Level(max(Level.BEGINNER, self.level(domain) - 1))
        self.set(domain, level)
        return level

    def observe(self, domain: str, technical_terms: int) -> Level:
        """Raise the level one step when the user shows familiarity with the domain."""
        current = self.level(domain)
        if technical_terms >= RAISE_THRESHOLD and current < Level.EXPERT:
            self.set(domain, Level(current + 1))
        return self.level(domain)


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class StyleMetrics:
    sentences: int
    words: int
    technical_terms: int  # distinct technical concepts mentioned
    undefined_terms: int  # technical concepts mentioned without their gloss

    @property
    def words_per_sentence_x10(self) -> int:
        """Mean sentence length times ten (integer arithmetic keeps it deterministic)."""
        return (self.words * 10) // max(1, self.sentences)


def measure(text: str, lexicon: Lexicon) -> StyleMetrics:
    sentences = [s for s in _SENTENCE_END.split(text.strip()) if s]
    technical = sorted(
        {c for c in lexicon.scan(text) if (lx := lexicon.get(c)) is not None and lx.level >= 1}
    )
    folded = fold(text)
    undefined = [
        c
        for c in technical
        if not ((lx := lexicon.get(c)) is not None and lx.gloss and fold(lx.gloss) in folded)
    ]
    return StyleMetrics(len(sentences), len(words(folded)), len(technical), len(undefined))
