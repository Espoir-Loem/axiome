"""Turns answered by reasoning, calculation or the clock: never by a web search."""

from __future__ import annotations

from datetime import timezone

import pytest

from axiome.core.clock import FixedClock
from axiome.dialogue.events import Searching, Thinking
from axiome.dialogue.layout import render
from axiome.dialogue.session import Session
from axiome.kernel import Kernel
from axiome.research.providers.wikipedia import Wikipedia
from axiome.team.researcher import Researcher
from tests.fakes import FakeFetcher, wikipedia_routes

NOW = "2026-03-01T09:05:00+00:00"


def session(lang: str = "fr") -> Session:
    web = Researcher([Wikipedia(FakeFetcher(wikipedia_routes(lang)))])
    return Session(Kernel.in_memory(FixedClock(NOW)), lang, web, timezone=timezone.utc)


def answer(s: Session, text: str) -> str:
    """Play one turn; it must not search the web."""
    events = list(s.respond(text))
    assert not any(isinstance(e, Searching) for e in events), text
    return render(e for e in events if not isinstance(e, Thinking))


@pytest.mark.parametrize(
    ("lang", "question", "expected"),
    [
        ("fr", "combien font 2 + 2 ?", "2 + 2 = 4"),
        ("fr", "calcule 12 fois 7", "12 × 7 = 84"),
        ("fr", "combien fait 10 / 4 ?", "10 / 4 = 5/2, soit environ 2,5"),
        ("fr", "1 / 0", "La division par zéro n'est pas définie"),
        ("en", "what is 6 times 7?", "6 × 7 = 42"),
        ("en", "10 / 4", "10 / 4 = 5/2, about 2.5"),
        ("en", "2 ^ 0.5", "I can't read that calculation."),
    ],
)
def test_arithmetic(lang: str, question: str, expected: str) -> None:
    assert answer(session(lang), question).startswith(expected)


def test_clock_and_date() -> None:
    fr, en = session("fr"), session("en")
    assert answer(fr, "quel jour sommes-nous ?") == "Nous sommes le dimanche 1er mars 2026."
    assert answer(fr, "quelle heure est-il ?") == "Il est 9 h 05."
    assert answer(en, "what's the date?") == "Today is Sunday, March 1, 2026."
    assert answer(en, "what time is it?") == "It is 9:05."
    assert "météo" in answer(fr, "quel temps fait-il ?")


def test_small_talk_variants() -> None:
    s = session()
    assert answer(s, "comment je m'appelle ?").startswith("Tu ne me l'as pas encore dit.")
    answer(s, "je m'appelle Espoir")
    assert answer(s, "comment je m'appelle ?") == "Tu t'appelles Espoir."
    assert "Ça va" in answer(s, "salut, ça va ?")
    assert "programme" in answer(s, "tu es une IA ?")
    assert answer(s, "mdr") == "Content que ça te fasse rire."
    assert answer(s, "hmm") == "Je t'écoute."
    assert answer(s, "tu peux m'aider ?").startswith("Oui.")
    assert "asdfghjkl" in answer(s, "asdfghjkl")
    assert "pas encore écrire de code" in answer(s, "écris une fonction qui trie une liste")


def test_property_questions() -> None:
    fr, en = session("fr"), session("en")
    assert answer(fr, "le tri fusion est-il stable ?").startswith("Oui. Le tri fusion est stable")
    unknown = answer(fr, "le tri rapide est-il stable ?")
    assert unknown.startswith("Je ne sais pas") and "Oui" not in unknown
    assert answer(en, "is merge sort stable?").startswith("Yes.")
    assert answer(en, "is a unicorn stable?").startswith("I don't know")


def test_requirements() -> None:
    fr, en = session("fr"), session("en")
    no = answer(fr, "la recherche dichotomique marche-t-elle sur une liste non triée ?")
    assert no.startswith("Non. La recherche dichotomique exige une entrée triée.")
    assert answer(en, "does binary search work on an unsorted list?").startswith("No.")
    assert answer(en, "does binary search work on a sorted list?").startswith("Yes")
    assert "no particular requirement" in answer(en, "does merge sort work on a list?")


def test_why_and_false_premises() -> None:
    fr, en = session("fr"), session("en")
    why = answer(fr, "pourquoi le chat est-il un vertébré ?")
    assert why == "Parce que le chat est un mammifère et les mammifères sont des vertébrés."
    assert answer(fr, "pourquoi les chats sont-ils des oiseaux ?").startswith("Non.")
    assert answer(en, "why is a cat a vertebrate?").startswith("Because the cat is a mammal")


def test_compare_and_purpose() -> None:
    fr, en = session("fr"), session("en")
    diff = answer(fr, "quelle est la différence entre une pile et une file ?")
    assert diff.startswith("La pile et la file sont deux structures de données.")
    assert "LIFO" in diff and "FIFO" in diff
    assert "mammal" in answer(en, "what's the difference between a cat and a bird?")
    pattern = answer(fr, "quel patron utiliser pour notifier plusieurs objets d'un changement ?")
    assert "l'observateur" in pattern
    assert "decorator" in answer(en, "which pattern should I use to add responsibilities?")
    none = answer(fr, "quel patron utiliser pour cuire des pâtes ?")
    assert none.startswith("Je ne connais pas de patron")


def test_user_told_facts_are_answered_as_such() -> None:
    s = session()
    answer(s, "Félix est un chat.")
    reply = answer(s, "Félix est-il un animal ?")
    assert reply.startswith("Oui, d'après ce que tu m'as dit : Félix est un chat")
    assert "le Félix" not in reply  # a proper name takes no article


def test_follow_ups_use_the_topic() -> None:
    s = session()
    answer(s, "qu'est-ce qu'un chat ?")
    assert "colonne vertébrale" in answer(s, "quelles sont ses propriétés ?")
    answer(s, "qu'est-ce qu'un patron de conception ?")
    assert "patron" in answer(s, "donne-moi un exemple")


def test_who_and_why_search_the_web() -> None:
    s = session()
    events = list(s.respond("pourquoi le ciel est bleu ?"))
    assert any(isinstance(e, Searching) for e in events)
    events = list(s.respond("qui est Marie Curie ?"))
    assert any(isinstance(e, Searching) for e in events)


def test_compare_with_an_unknown_side_searches() -> None:
    s = session()
    events = list(s.respond("quelle est la différence entre une pile et un photon ?"))
    assert any(isinstance(e, Searching) for e in events)


def test_name_given_as_an_answer() -> None:
    s = session()
    assert answer(s, "c'est quoi mon nom").endswith("Comment t'appelles-tu ?")
    assert answer(s, "Espoir") == "Enchanté, Espoir."
    assert answer(s, "c'est quoi mon nom") == "Tu t'appelles Espoir."
    other = session()
    answer(other, "c'est quoi mon nom")
    answer(other, "merci")  # the expectation lasts one turn only
    assert "Enchanté" not in "".join(str(e) for e in other.respond("Paul"))


def test_limits_are_stated() -> None:
    assert "code" in answer(session("fr"), "quelles sont tes limites ?")
    assert "code" in answer(session("en"), "what are your limitations?")


def test_letters_after_a_clarification() -> None:
    s = session()
    assert "« L »" in answer(s, "c'est quoi l")
    reply = answer(s, "je parle bien de la lettre l")
    assert reply.startswith("**L** est la 12e lettre") and "consonne, la 9e" in reply
    assert "voyelle, la 1re" in answer(s, "c'est quoi la lettre a ?")
    answer(s, "c'est quoi h")
    assert "8e lettre" in answer(s, "oui")
    en = session("en")
    answer(en, "what is b")
    assert "the 1st consonant" in answer(en, "yes, the letter")
    assert "13th letter" in answer(en, "tell me about the letter m")
    assert "22nd letter" in answer(en, "the letter v")
