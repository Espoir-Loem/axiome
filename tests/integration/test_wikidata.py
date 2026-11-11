"""Learning from Wikidata: classes, names, genders, lineages, and their use in answers."""

from __future__ import annotations

from datetime import timezone

from axiome.core.clock import FixedClock
from axiome.dialogue.events import Thinking
from axiome.dialogue.layout import render
from axiome.dialogue.session import Session
from axiome.kernel import Kernel
from axiome.knowledge.wikidata import Librarian, Wikidata
from axiome.verification.epistemic import Status
from tests.wikidata_fake import FakeWikidata


def library(kernel: Kernel | None = None) -> tuple[Librarian, FakeWikidata]:
    fake = FakeWikidata()
    wd = Wikidata(fake, interval_s=0)
    return Librarian(kernel or Kernel.in_memory(FixedClock()), wd, depth=2), fake


def test_class_import_ignores_metaclasses_and_keeps_provenance() -> None:
    lib, _ = library()
    done = lib.learn("trou noir", "fr")
    assert done.concept == "black_hole"
    state = lib.kernel.state
    facts = {str(f) for f in state.model.facts() if f.predicate == "is_a"}
    assert "is_a(black_hole, astronomical_object)" in facts
    assert not any("type_of" in f for f in facts)  # "instance of" on a class is a metaclass
    atom = next(f for f in state.model.facts() if str(f) == "is_a(black_hole, astronomical_object)")
    assert state.assessments[atom].status is Status.PLAUSIBLE  # one reference: not confirmed
    words = {w.form: w for w in lib.kernel.store.words("fr")}
    assert words["trou noir"].gender == "m" and words["objet céleste"].gender == "m"
    again = lib.learn("trou noir", "fr")
    assert again.facts == 0 and again.words == 0  # idempotent


def test_untranslated_classes_are_skipped_and_genders_guessed() -> None:
    lib, _ = library()
    lib.learn("naine jaune", "fr")
    words = {w.form: w for w in lib.kernel.store.words("fr")}
    assert words["étoile"].gender == "f"  # Wikidata Lexemes
    assert words["naine jaune"].gender == "f"  # no lexeme: "-ine" ending
    assert "dark thing" not in words


def test_disambiguation_and_case() -> None:
    lib, _ = library()
    assert lib.wikidata.find("lion", "fr") == "Q3"  # not the constellation "Lion"
    assert lib.wikidata.find("Lion", "fr") == "Q3"  # Q8 is a disambiguation item
    assert lib.learn("zorglub", "fr").concept is None


def test_people_are_proper_names() -> None:
    lib, _ = library()
    lib.learn("Marie Curie", "fr")
    words = {w.form: w for w in lib.kernel.store.words("fr")}
    assert words["Marie Curie"].proper


def test_lineage_and_same_name_goal() -> None:
    lib, _ = library()
    lib.learn("lion", "fr")
    goal = lib.qid("mammal", "mammifère", "fr")
    assert goal == "Q7"
    child = lib.qid("lion", "lion", "fr")
    done = lib.connect(str(child), str(goal), "fr")
    assert done.concept == "lion" and "mammal" in done.concepts
    assert lib.connect(str(child), "Q11", "fr", max_depth=3).concept is None
    assert lib.connect(str(child), "Q999", "fr").concept is None


def session() -> tuple[Session, FakeWikidata]:
    kernel = Kernel.in_memory(FixedClock())
    lib, fake = library(kernel)
    return Session(kernel, "fr", None, timezone=timezone.utc, librarian=lib), fake


def answer(s: Session, text: str) -> tuple[str, list[str]]:
    events = list(s.respond(text))
    thinking = [e.text for e in events if isinstance(e, Thinking)]
    return render(e for e in events if not isinstance(e, Thinking)), thinking


def test_yes_no_questions_learn_on_demand() -> None:
    s, fake = session()
    text, thinking = answer(s, "le lion est-il un mammifère ?")
    assert text.startswith("Oui. Le lion est un mammifère.")
    assert "Fiabilité" in text and "plausible" not in text  # one note, no inline hedge
    assert any("Wikidata" in t for t in thinking)
    text, _ = answer(s, "le lion est-il un oiseau ?")
    assert text.startswith("Non. Le lion est un mammifère")
    why, _ = answer(s, "pourquoi le lion est-il un mammifère ?")
    assert why.startswith("Parce que le lion est un Panthera")
    calls = len(fake.calls)
    answer(s, "le lion est-il un mammifère ?")
    assert len(fake.calls) == calls  # known now: no new request


def test_definition_from_wikidata_comes_first() -> None:
    s, _ = session()
    answer(s, "le trou noir est-il un objet céleste ?")
    text, _ = answer(s, "qu'est-ce qu'un trou noir ?")
    assert text.startswith("Trou noir : objet céleste très compact.")
    assert "- Le trou noir est un objet céleste." in text
    assert "https://www.wikidata.org/wiki/Q1" in text
