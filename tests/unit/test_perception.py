"""Normalization and the analyst (intent + mention resolution)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from axiome.dialogue.level import Level
from axiome.language.pack import load_pack
from axiome.perception.normalize import fold, prepare, slug, squash, words
from axiome.team.analyst import Analyst, Context, Intent, Mention


@given(st.text())
def test_fold_preserves_length(text: str) -> None:
    assert len(fold(text)) == len(text)


def test_normalize_helpers() -> None:
    assert fold("Qu’est-ce QU'Été") == "qu'est-ce qu'ete"
    assert squash("  le   chat  ? ") == "le chat?"
    assert prepare("Où  est l’arbre !") == "ou est l'arbre!"
    assert words("l'arbre est-il vert") == ["l'arbre", "est-il", "vert"]
    assert slug("Le Photon") == "le_photon"
    assert slug("2D graph") == "n_2d_graph"
    assert slug("?!") == ""


FR = Analyst(load_pack("fr"))
EN = Analyst(load_pack("en"))


@pytest.mark.parametrize(
    ("text", "intent", "subject"),
    [
        ("Bonjour !", Intent.GREETING, None),
        ("merci beaucoup", Intent.THANKS, None),
        ("au revoir", Intent.FAREWELL, None),
        ("Qui es-tu ?", Intent.IDENTITY, None),
        ("que sais-tu faire ?", Intent.CAPABILITIES, None),
        ("je n'ai pas compris", Intent.CONFUSION, None),
        ("Qu'est-ce qu'un chat ?", Intent.DEFINITION, "cat"),
        ("c'est quoi une pile", Intent.DEFINITION, "stack"),
        ("explique-moi ce qu'est le tri fusion", Intent.DEFINITION, "merge_sort"),
        ("la table de hachage, c'est quoi ?", Intent.DEFINITION, "hash_table"),
        ("baleine", Intent.DEFINITION, "whale"),
        ("Quelles sont les propriétés du chat ?", Intent.PROPERTIES, "cat"),
        ("l'unité de la masse ?", Intent.UNIT, "mass"),
        ("en quoi se mesure l'énergie ?", Intent.UNIT, "energy"),
        ("quelle est la complexité du tri rapide ?", Intent.COMPLEXITY, "quicksort"),
        ("quels sont les algorithmes de tri ?", Intent.MEMBERS, "sorting_algorithm"),
        ("donne-moi des exemples de mammifères", Intent.MEMBERS, "mammal"),
        ("cherche le tri fusion", Intent.RESEARCH, "merge_sort"),
        ("le chat est-il un oiseau ?", Intent.CHECK_IS_A, "cat"),
        ("Félix est un chat.", Intent.TEACH_IS_A, None),
        ("bla bla bla bla bla bla bla", Intent.UNKNOWN, None),
    ],
)
def test_french_intents(text: str, intent: Intent, subject: str | None) -> None:
    analysis = FR.analyze(text, Context())
    assert analysis.intent is intent
    if subject is not None:
        assert analysis.subject is not None and analysis.subject.concept == subject


@pytest.mark.parametrize(
    ("text", "intent", "subject"),
    [
        ("Hello!", Intent.GREETING, None),
        ("what is a binary search tree?", Intent.DEFINITION, "binary_search_tree"),
        ("examples of design patterns", Intent.MEMBERS, "design_pattern"),
        ("what are the properties of a stack?", Intent.PROPERTIES, "stack"),
        ("what is the unit of force?", Intent.UNIT, "force"),
        ("complexity of heapsort", Intent.COMPLEXITY, "heapsort"),
        ("is a whale a mammal?", Intent.CHECK_IS_A, "whale"),
        ("Felix is a cat.", Intent.TEACH_IS_A, None),
    ],
)
def test_english_intents(text: str, intent: Intent, subject: str | None) -> None:
    analysis = EN.analyze(text, Context())
    assert analysis.intent is intent
    if subject is not None:
        assert analysis.subject is not None and analysis.subject.concept == subject


def test_level_requests_and_waivers() -> None:
    a = FR.analyze("explique simplement ce qu'est un graphe", Context())
    assert a.intent is Intent.DEFINITION and a.level is Level.BEGINNER
    assert a.subject is not None and a.subject.concept == "graph"
    only = FR.analyze("explique-moi plus simplement", Context())
    assert only.intent is Intent.LEVEL and only.level is Level.BEGINNER
    assert EN.analyze("expert level", Context()).intent is Intent.LEVEL
    assert "S5" in FR.analyze("un chat avec des emojis", Context()).waivers


def test_context_pronouns_follow_ups_and_ambiguity() -> None:
    topic = Mention("chat", ("cat",))
    ctx = Context(topic=topic, intent=Intent.PROPERTIES)
    follow = FR.analyze("et le chien ?", ctx)
    assert follow.intent is Intent.PROPERTIES
    assert follow.subject is not None and follow.subject.concept == "dog"
    pron = FR.analyze("qu'est-ce que c'est que lui ?", ctx)
    assert pron.subject is not None
    it = FR.resolve("lui", "lui", ctx)
    assert it is topic
    lost = FR.resolve("lui", "lui", Context())
    assert lost.pronoun and lost.concept is None
    ambiguous = Mention("x", ("a", "b"))
    assert ambiguous.ambiguous and ambiguous.concept is None
    assert FR.analyze("et lui ?", Context()).intent is Intent.DEFINITION


def test_technical_vocabulary_is_counted() -> None:
    a = FR.analyze(
        "dans un graphe acyclique et une table de hachage, qu'est-ce qu'un tas ?", Context()
    )
    assert a.technical_terms >= 2 and a.domain == "computing"
