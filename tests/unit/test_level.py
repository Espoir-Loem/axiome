"""Adaptive level profile and style metrics."""

from __future__ import annotations

from axiome.dialogue.level import DEFAULT_LEVEL, Level, LevelProfile, measure
from axiome.knowledge.store import KnowledgeStore
from axiome.language.pack import load_pack


def test_profile_signals_and_persistence() -> None:
    store = KnowledgeStore()
    profile = LevelProfile(store)
    assert profile.level("physics") is DEFAULT_LEVEL
    profile.set("physics", Level.BEGINNER)
    assert profile.level("physics") is Level.BEGINNER  # falsy enum value must still count
    assert profile.lower("physics") is Level.BEGINNER
    assert profile.observe("computing", 1) is Level.INTERMEDIATE
    assert profile.observe("computing", 2) is Level.EXPERT
    assert profile.observe("computing", 5) is Level.EXPERT
    profile.set("*", Level.EXPERT)
    assert profile.level("biology") is Level.EXPERT
    again = LevelProfile(store)
    assert again.level("physics") is Level.BEGINNER and again.level("computing") is Level.EXPERT
    assert LevelProfile().lower("x") is Level.BEGINNER


def test_measure() -> None:
    lexicon = load_pack("fr").lexicon
    plain = measure("Le chat dort. Le chien court.", lexicon)
    assert (plain.sentences, plain.words, plain.technical_terms) == (2, 6, 0)
    assert plain.words_per_sentence_x10 == 30
    technical = measure("Le chat est un mammifère. Un tas est rapide.", lexicon)
    assert technical.technical_terms == 2 and technical.undefined_terms == 2
    gloss = lexicon.get("mammal")
    assert gloss is not None
    defined = measure(f"Le chat est un mammifère. Un mammifère, c'est {gloss.gloss}.", lexicon)
    assert defined.undefined_terms == 0
