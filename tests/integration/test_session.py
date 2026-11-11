"""Conversations end to end: levels, honesty, teaching, web research and learning."""

from __future__ import annotations

import time

import pytest

from axiome.core.clock import FixedClock
from axiome.dialogue.events import Done, Say, Searching, SourceFound, Thinking
from axiome.dialogue.level import Level, measure
from axiome.dialogue.session import Session
from axiome.kernel import Kernel
from axiome.research.providers.wikipedia import Wikipedia
from axiome.team.researcher import Researcher
from tests.fakes import FakeFetcher, wikipedia_routes


def fresh(lang: str = "fr", researcher: Researcher | None = None) -> Session:
    return Session(Kernel.in_memory(FixedClock()), lang, researcher)


def web(lang: str = "fr") -> Researcher:
    return Researcher([Wikipedia(FakeFetcher(wikipedia_routes(lang)))])


def test_social_turns() -> None:
    s = fresh()
    assert s.answer_text("Bonjour") == "Bonjour. Je t'écoute."
    assert s.answer_text("merci") == "Avec plaisir."
    assert "Axiome" in s.answer_text("qui es-tu ?")
    assert "niveau" in s.answer_text("que sais-tu faire ?")
    assert s.answer_text("au revoir") == "À bientôt."
    assert "reformuler" in s.answer_text("bla bla bla bla bla bla bla")


def test_definition_by_level_keeps_the_same_truth() -> None:
    beginner, expert = fresh(), fresh()
    beginner.profile.set("biology", Level.BEGINNER)
    expert.profile.set("biology", Level.EXPERT)
    low = [e for e in beginner.respond("qu'est-ce qu'un chat ?") if isinstance(e, Say)]
    high = [e for e in expert.respond("qu'est-ce qu'un chat ?") if isinstance(e, Say)]
    facts_low = {f for e in low for f in e.support if not f.startswith("lexicon:")}
    facts_high = {f for e in high for f in e.support}
    assert facts_low <= facts_high  # simplifying never says something different
    lexicon = beginner.pack.lexicon
    m_low = measure(" ".join(e.text for e in low), lexicon)
    m_high = measure(" ".join(e.text for e in high), lexicon)
    assert m_low.undefined_terms == 0 < m_high.undefined_terms
    assert "Statut : PROUVÉ" in " ".join(e.text for e in high)
    assert "Classification" in " ".join(e.text for e in high)
    assert "c'est un animal" in " ".join(e.text for e in low)


def test_level_requests_rephrase_the_topic() -> None:
    s = fresh()
    s.answer_text("qu'est-ce qu'un graphe ?")
    simple = s.answer_text("explique plus simplement")
    assert simple.startswith("D'accord, je reprends plus simplement.")
    assert "ensemble de points" in simple
    expert = s.answer_text("niveau expert")
    assert "Statut : PROUVÉ" in expert and "\n- Classification" in expert
    assert s.answer_text("je n'ai pas compris").startswith("D'accord")
    assert s.profile.level("computing") is Level.INTERMEDIATE  # one step down from expert


def test_specific_questions() -> None:
    s = fresh()
    assert "kilogramme" in s.answer_text("quelle est l'unité de la masse ?")
    assert "O(n log n)" in s.answer_text("quelle est la complexité du tri fusion ?")
    members = s.answer_text("quels sont les patrons de création ?")
    assert "le singleton" in members and "la fabrique" in members
    assert "stable" in s.answer_text("quelles sont les propriétés du tri fusion ?")
    assert "colonne vertébrale" in s.answer_text("et le chien ?")  # follow-up keeps the intent
    en = fresh("en")
    assert en.answer_text("what is the SI unit of length?") == "The SI unit of length is the metre."


def test_checks_answer_yes_no_or_unknown_honestly() -> None:
    s = fresh()
    assert s.answer_text("le chat est-il un mammifère ?").startswith("Oui.")
    no = s.answer_text("le chat est-il un oiseau ?")
    assert no.startswith("Non. Le chat est un mammifère")
    # no known incompatibility between animals and algorithms: honest "I don't know"
    assert s.answer_text("le chat est-il un algorithme ?").startswith("Je ne sais pas")
    unknown = s.answer_text("le chat est-il un robot ?")
    assert "ne veut pas dire que c'est faux" in unknown
    assert fresh("en").answer_text("is a cat a bird?").startswith("No.")


def test_teaching() -> None:
    s = fresh()
    assert s.answer_text("Félix est un chat.").startswith("Noté.")
    assert "Non vérifié" in s.answer_text("qu'est-ce que Félix ?")
    assert s.answer_text("le chat est un mammifère.") == "Je le savais déjà."
    refused = s.answer_text("le chat est un oiseau.")
    assert refused.startswith("Je ne peux pas l'accepter")
    s.answer_text("la tomate est une plante.")
    assert "une plante" in s.answer_text("qu'est-ce qu'une tomate ?")
    again = Session(s.kernel, "fr")  # learned words survive a new session
    assert again.pack.lexicon.lookup("tomate") == ("tomate",)


def test_unknown_topic_offline_says_so() -> None:
    out = fresh().answer_text("qu'est-ce qu'un photon ?")
    assert out == (
        "Je ne connais pas encore « photon ». "
        "Je suis hors ligne, je ne peux donc pas chercher pour l'instant."
    )


def test_pronoun_without_topic_and_ambiguity() -> None:
    s = fresh()
    assert s.answer_text("et lui ?") == "De quel sujet parles-tu ?"
    s.pack.lexicon.learn("chose", "cat")
    s.pack.lexicon.learn("chose", "dog")
    assert (
        s.answer_text("qu'est-ce qu'une chose ?")
        == "Tu parles de quoi exactement : chat et chien ?"
    )


def test_web_research_streams_cites_and_learns() -> None:
    s = fresh(researcher=web())
    start = time.monotonic()
    events = list(s.respond("qu'est-ce qu'un photon ?"))
    assert isinstance(events[0], Thinking) and time.monotonic() - start < 5
    kinds = [type(e) for e in events]
    assert kinds.index(Searching) < kinds.index(SourceFound) < kinds.index(Say)
    says = [e for e in events if isinstance(e, Say)]
    assert says[0].role == "lead"
    assert says[0].text.startswith("Le **photon** est la particule élémentaire")
    assert says[0].text.endswith("[1]")
    assert [e.role for e in says[1:]].count("point") >= 1
    assert all(e.support for e in says if e.status is not None)
    assert isinstance(events[-1], Done) and events[-1].blocked == 0
    answer = fresh(researcher=web()).answer_text("qu'est-ce qu'un photon ?")
    assert "\n\n- " in answer
    assert "Voir aussi : Photonique." in answer
    assert "Fiabilité : une seule source fiable pour l'instant, à recouper." in answer
    assert answer.endswith(
        "Sources :\n[1] Wikipedia (fr), « Photon » : https://fr.wikipedia.org/wiki/Photon"
    )
    assert "(plausible" not in answer  # one reliability note, not a hedge in every sentence
    offline = Session(s.kernel, "fr")  # no researcher: answers from what it learned
    replay = offline.answer_text("qu'est-ce qu'un photon ?")
    assert replay.startswith("Le photon est la particule élémentaire")
    assert "Sources :\n[1] Wikipedia (fr) : https://fr.wikipedia.org/wiki/Photon" in replay


def test_web_research_failure_and_english() -> None:
    nothing = Researcher([Wikipedia(FakeFetcher({}))])
    assert fresh(researcher=nothing).answer_text("cherche photon") == (
        "Je n'ai trouvé aucune source exploitable sur « photon »."
    )
    en = fresh("en", web("en")).answer_text("what is a photon?")
    assert en.startswith("A **photon** is an elementary particle")


def test_small_talk_is_never_searched() -> None:
    s = fresh(researcher=web())
    assert s.answer_text("comment vas tu") == "Ça va bien, merci. Et toi ?"
    assert s.answer_text("bien et toi") == "Tant mieux."
    assert s.answer_text("tu t'appelles comment ?") == "Je m'appelle Axiome."
    assert s.answer_text("je m'appelle espoir") == "Enchanté, Espoir."
    assert s.answer_text("salut") == "Bonjour, Espoir."
    assert s.answer_text("ok") == "D'accord."
    events = list(s.respond("tu aimes la musique ?"))
    assert not any(isinstance(e, Searching) for e in events)
    assert "Je ne sais pas encore bien répondre" in s.answer_text("tu aimes la musique ?")
    en = fresh("en", web("en"))
    assert en.answer_text("how are you") == "I'm doing well, thanks. And you?"
    assert en.answer_text("what's your name?") == "My name is Axiome."
    assert en.answer_text("do you like music?").startswith("I can't really answer that yet.")


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_answers_carry_no_ai_tells(lang: str) -> None:
    s = fresh(lang, web(lang))
    questions = {
        "fr": ["Bonjour", "qu'est-ce qu'un tas ?", "qu'est-ce qu'un photon ?", "merci"],
        "en": ["Hello", "what is a heap?", "what is a photon?", "thanks"],
    }[lang]
    for q in questions:
        for event in s.respond(q):
            if isinstance(event, Say):
                assert s.reviewer.style(event.text)[1] == [], event.text


def test_incomplete_input_is_clarified_not_searched() -> None:
    s = fresh(researcher=web())
    for text in ("h", "?", "..."):
        events = list(s.respond(text))
        assert not any(isinstance(e, Searching) for e in events)
        assert s.answer_text(text) == "Ton message semble incomplet. Que voulais-tu demander ?"
    assert s.answer_text("c'est quoi l") == (
        "Tu parles de la lettre « L », ou ta question a été coupée ?"
    )
    typo = s.answer_text("qu'est-ce qu'un chta ?")
    assert typo.startswith("Je pense que tu parles de « chat ».\n\nLe **chat** est un mammifère.")
    assert fresh("en").answer_text("h") == (
        "Your message looks incomplete. What did you want to ask?"
    )
