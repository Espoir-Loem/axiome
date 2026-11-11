"""Language packs: morphology, lexicon, templates."""

from __future__ import annotations

import json
import string
from importlib import resources

import pytest

from axiome.core.errors import KnowledgeError
from axiome.language.lexicon import Lexeme
from axiome.language.morphology import English, French
from axiome.language.pack import load_pack, pack_digest

FR = French("présente « {lemma} »")
EN = English('has "{lemma}"')


@pytest.mark.parametrize(
    ("lexeme", "spec", "expected"),
    [
        (Lexeme("cat", "chat"), "def", "le chat"),
        (Lexeme("whale", "baleine", gender="f"), "def", "la baleine"),
        (Lexeme("tree", "arbre"), "def", "l'arbre"),
        (Lexeme("energy", "énergie", gender="f"), "of_def", "de l'énergie"),
        (Lexeme("mass", "masse", gender="f"), "of_def", "de la masse"),
        (Lexeme("time", "temps"), "of_def", "du temps"),
        (Lexeme("whale", "baleine", gender="f"), "indef", "une baleine"),
        (Lexeme("bird", "oiseau"), "pl", "oiseaux"),
        (Lexeme("animal", "animal"), "def_pl", "les animaux"),
        (Lexeme("time", "temps"), "pl", "temps"),
        (Lexeme("tree", "arbre"), "de_pl", "d'arbres"),
        (Lexeme("cat", "chat"), "de_pl", "de chats"),
        (Lexeme("algo", "algorithme de tri"), "pl", "algorithmes de tri"),
        (Lexeme("x", "x", pred="vole"), "pred", "vole"),
        (Lexeme("x", "stable"), "pred", "présente « stable »"),
        (Lexeme("cat", "chat"), "bare", "chat"),
    ],
)
def test_french(lexeme: Lexeme, spec: str, expected: str) -> None:
    assert FR.form(lexeme, spec) == expected


@pytest.mark.parametrize(
    ("lexeme", "spec", "expected"),
    [
        (Lexeme("cat", "cat"), "indef", "a cat"),
        (Lexeme("array", "array"), "gen", "an array"),
        (Lexeme("q", "SI base quantity"), "indef", "an SI base quantity"),
        (Lexeme("p", "SOLID principle"), "indef", "a SOLID principle"),
        (Lexeme("length", "length", mass=True), "gen", "length"),
        (Lexeme("length", "length", mass=True), "of_def", "of length"),
        (Lexeme("cat", "cat"), "of_def", "of the cat"),
        (Lexeme("qs", "quicksort", proper=True), "def", "quicksort"),
        (Lexeme("cat", "cat"), "def", "the cat"),
        (Lexeme("box", "box"), "pl", "boxes"),
        (Lexeme("q", "physical quantity"), "def_pl", "the physical quantities"),
        (Lexeme("day", "day"), "pl", "days"),
        (Lexeme("energy", "energy", mass=True), "pl", "energy"),
        (Lexeme("x", "x"), "pred", 'has "x"'),
        (Lexeme("cat", "cat"), "whatever", "cat"),
    ],
)
def test_english(lexeme: Lexeme, spec: str, expected: str) -> None:
    assert EN.form(lexeme, spec) == expected


def test_lexicon_lookup_scan_learn() -> None:
    lexicon = load_pack("fr").lexicon
    assert lexicon.lookup("Chats") == ("cat",)
    assert lexicon.lookup("table de hachage") == ("hash_table",)
    assert lexicon.lookup("pingouin") == ("penguin",)
    assert lexicon.lookup("photon") == ()
    assert lexicon.scan("le tri fusion et la table de hachage") == ["merge_sort", "hash_table"]
    learned = lexicon.learn("Photon", "photon", "m")
    assert learned.learned and lexicon.lookup("photon") == ("photon",)
    assert lexicon.learn("photon", "photon") is lexicon.get("photon")
    alias = lexicon.learn("minou", "cat")
    assert "minou" in alias.aliases and lexicon.lookup("minou") == ("cat",)
    assert lexicon.lexeme("unknown_thing").lemma == "unknown thing"
    assert str(lexicon.phrase("cat")) == "chat"
    assert format(lexicon.phrase("cat"), "") == "chat"
    assert load_pack("fr").lexicon.lookup("photon") == ()  # learning never leaks


def test_say_and_join() -> None:
    fr, en = load_pack("fr"), load_pack("en")
    lx = fr.lexicon
    assert fr.say("is_a", s=lx.phrase("cat"), o=lx.phrase("mammal")) == "Le chat est un mammifère."
    assert fr.say("si_unit", q=lx.phrase("energy"), u=lx.phrase("joule")) == (
        "L'unité SI de l'énergie est le joule."
    )
    assert en.say("si_unit", q=en.lexicon.phrase("length"), u=en.lexicon.phrase("metre")) == (
        "The SI unit of length is the metre."
    )
    assert fr.join(["a", "b", "c"]) == "a, b et c" and en.join(["a"]) == "a"
    assert pack_digest("fr") != pack_digest("en")
    with pytest.raises(KnowledgeError):
        load_pack("xx")


def _read(code: str, name: str) -> dict[str, object]:
    base = resources.files("axiome.data.lang").joinpath(code)
    data: dict[str, object] = json.loads(base.joinpath(name).read_text("utf-8"))
    return data


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_packs_are_parallel() -> None:
    fr, en = _read("fr", "grammar.json"), _read("en", "grammar.json")
    ft, et = fr["templates"], en["templates"]
    assert isinstance(ft, dict) and isinstance(et, dict)
    assert set(ft) == set(et)
    for key in ft:
        assert _fields(ft[key]) == _fields(et[key]), key
    fl, el = _read("fr", "lexicon.json")["concepts"], _read("en", "lexicon.json")["concepts"]
    assert isinstance(fl, dict) and isinstance(el, dict)
    assert set(fl) == set(el)
    for concept in fl:
        assert bool(fl[concept].get("gloss")) == bool(el[concept].get("gloss")), concept
        assert bool(fl[concept].get("pred")) == bool(el[concept].get("pred")), concept
    fi, ei = _read("fr", "intents.json")["intents"], _read("en", "intents.json")["intents"]
    assert isinstance(fi, list) and isinstance(ei, list)
    assert {i[0] for i in fi} == {i[0] for i in ei}


def test_every_seed_concept_has_words() -> None:
    from axiome.core.clock import FixedClock  # noqa: PLC0415
    from axiome.kernel import Kernel  # noqa: PLC0415

    kernel = Kernel.in_memory(FixedClock())
    concepts = {
        str(a)
        for f in kernel.state.model.facts()
        for a in f.args
        if isinstance(a, str) and a.isidentifier() and not a.startswith("O(")
    }
    for code in ("fr", "en"):
        lexicon = load_pack(code).lexicon
        missing = sorted(c for c in concepts if lexicon.get(c) is None)
        assert not missing, (code, missing)


def test_typo_correction() -> None:
    from axiome.language.lexicon import edit_distance  # noqa: PLC0415

    assert edit_distance("chta", "chat", 2) == 1  # adjacent swap
    assert edit_distance("abc", "xyz", 1) == 2  # stops past the limit
    lexicon = load_pack("fr").lexicon
    assert lexicon.closest("chta") == ("cat",)
    assert lexicon.closest("tabel de hachage") == ("hash_table",)
    assert lexicon.closest("tas") == ()  # too short to correct
    assert lexicon.closest("zzzzzzzz") == ()
    assert lexicon.closest("pila") == ("stack",)  # "pile"
