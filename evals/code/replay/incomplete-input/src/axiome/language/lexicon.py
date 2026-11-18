"""Lexicon: links surface words of one language to canonical knowledge concepts.

Concepts (``cat``, ``merge_sort``) are language independent; a lexeme gives the
words used for a concept in one language, with what morphology needs (gender,
irregular plural, mass/proper noun) and what the adaptive writer needs
(technicality level, plain-language gloss, domain).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Protocol

from axiome.perception.normalize import fold, words

GENERAL_DOMAIN = "general"


@dataclass(frozen=True, slots=True)
class Lexeme:
    concept: str
    lemma: str
    domain: str = GENERAL_DOMAIN
    level: int = 0  # 0 everyday word, 1 technical, 2 specialist
    gender: str = "m"
    plural: str = ""  # irregular or multi-word plural; empty means "apply the rules"
    gloss: str = ""  # plain-language definition, with its article
    pred: str = ""  # verb phrase for a property ("allaite ses petits")
    mass: bool = False  # uncountable noun (English article rules)
    proper: bool = False  # named thing, used without article in English
    aliases: tuple[str, ...] = ()
    learned: bool = False  # acquired at run time, not curated


class Morphology(Protocol):
    def plural(self, lexeme: Lexeme) -> str: ...

    def form(self, lexeme: Lexeme, spec: str) -> str: ...


class Lexicon:
    def __init__(self, language: str, morphology: Morphology, lexemes: Iterable[Lexeme]) -> None:
        self.language = language
        self.morphology = morphology
        self._by_concept: dict[str, Lexeme] = {}
        self._forms: dict[str, set[str]] = {}
        self._max_words = 1
        for lexeme in lexemes:
            self.add(lexeme)

    def add(self, lexeme: Lexeme) -> None:
        self._by_concept[lexeme.concept] = lexeme
        forms = {lexeme.lemma, self.morphology.plural(lexeme), *lexeme.aliases}
        forms.add(lexeme.concept.replace("_", " "))
        for form in forms:
            key = " ".join(words(fold(form)))
            if key:
                self._forms.setdefault(key, set()).add(lexeme.concept)
                self._max_words = max(self._max_words, len(key.split()))

    def get(self, concept: str) -> Lexeme | None:
        return self._by_concept.get(concept)

    def lexeme(self, concept: str) -> Lexeme:
        """The lexeme of a concept, synthesized from its identifier if unknown."""
        known = self._by_concept.get(concept)
        return known or Lexeme(concept, concept.replace("_", " "), learned=True)

    def phrase(self, concept: str) -> NounPhrase:
        return NounPhrase(self.lexeme(concept), self.morphology)

    def lookup(self, form: str) -> tuple[str, ...]:
        """Concepts a phrase may denote, sorted (empty if unknown)."""
        key = " ".join(words(fold(form)))
        return tuple(sorted(self._forms.get(key, ())))

    def scan(self, text: str) -> list[str]:
        """Known concepts mentioned in ``text``, longest match first, in reading order."""
        tokens = words(fold(text))
        found: list[str] = []
        i = 0
        while i < len(tokens):
            for n in range(min(self._max_words, len(tokens) - i), 0, -1):
                concepts = self._forms.get(" ".join(tokens[i : i + n]))
                if concepts:
                    found.extend(sorted(concepts))
                    i += n
                    break
            else:
                i += 1
        return found

    def learn(self, form: str, concept: str, gender: str = "m") -> Lexeme:
        """Record that ``form`` names ``concept`` (creating the lexeme if needed)."""
        current = self._by_concept.get(concept)
        if current is None:
            lexeme = Lexeme(concept, form.strip(), gender=gender, learned=True)
        elif fold(form) in {fold(current.lemma), *map(fold, current.aliases)}:
            return current
        else:
            lexeme = replace(current, aliases=(*current.aliases, form.strip()))
        self.add(lexeme)
        return lexeme


@dataclass(frozen=True, slots=True)
class NounPhrase:
    """A concept ready to be inflected: ``format(np, "def")`` -> ``"le chat"``."""

    lexeme: Lexeme
    morphology: Morphology

    def __format__(self, spec: str) -> str:
        return self.morphology.form(self.lexeme, spec or "bare")

    def __str__(self) -> str:
        return self.lexeme.lemma
