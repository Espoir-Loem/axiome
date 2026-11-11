"""Loading of language packs (``axiome/data/lang/<code>/``).

A pack is pure data: ``lexicon.json`` (words), ``grammar.json`` (sentence
templates), ``intents.json`` (understanding patterns) and ``style.json``
(forbidden AI tells, see ``docs/signes-ia.md``). Adding a language means adding
a pack plus a :class:`~axiome.language.lexicon.Morphology` implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from axiome.core.errors import KnowledgeError
from axiome.language.lexicon import Lexeme, Lexicon, Morphology
from axiome.language.morphology import English, French

PACKAGE = "axiome.data.lang"
FILES = ("lexicon.json", "grammar.json", "intents.json", "style.json")
_AFTER_STOP = re.compile(r"([.!?] )([a-zà-ÿ])")
_MORPHOLOGY: dict[str, type[French] | type[English]] = {"fr": French, "en": English}


@cache
def _raw(code: str) -> dict[str, Any]:
    if code not in _MORPHOLOGY:
        raise KnowledgeError("language.unsupported", code=code)
    base = resources.files(PACKAGE).joinpath(code)
    return {name: json.loads(base.joinpath(name).read_text("utf-8")) for name in FILES}


def pack_digest(code: str) -> str:
    h = hashlib.sha256()
    base = resources.files(PACKAGE).joinpath(code)
    for name in FILES:
        h.update(name.encode())
        h.update(base.joinpath(name).read_bytes())
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class StyleRules:
    rules: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...]  # (category, patterns)
    waivers: Mapping[str, re.Pattern[str]]  # category -> request that lifts it


@dataclass(frozen=True)
class LanguagePack:
    code: str
    lexicon: Lexicon
    templates: Mapping[str, str]
    list_separator: str
    list_last: str
    intents: tuple[tuple[str, re.Pattern[str]], ...]
    articles: tuple[str, ...]
    pronouns: frozenset[str]
    stopwords: frozenset[str]
    personal_markers: frozenset[str]  # words showing the user talks to/about Axiome or self
    level_signals: Mapping[str, re.Pattern[str]]
    level_only: re.Pattern[str]  # what remains of a pure level request ("explique")
    style: StyleRules
    greeting_prefix: re.Pattern[str]  # "salut, ..." in front of a real question
    laughter: re.Pattern[str]
    filler: re.Pattern[str]
    operators: Mapping[str, str]  # spoken arithmetic ("fois") -> symbol
    arith_prefix: re.Pattern[str]  # "combien font", "calcule"
    weekdays: tuple[str, ...]
    months: tuple[str, ...]
    negations: frozenset[str]
    disambiguation: re.Pattern[str]  # a web page listing meanings, not defining one
    negative_prefixes: tuple[str, ...]  # "unsorted" -> sorted, negated
    letter_confirm: re.Pattern[str]  # "yes, the letter" after Axiome asked
    vowels: str
    languages: Mapping[str, str]  # language name as typed ("anglais") -> code
    language_names: Mapping[str, str]  # code -> name, for answers
    continuers: frozenset[str]  # "et", "and": a message continuing the previous one

    def say(self, key: str, **slots: object) -> str:
        """Realize a sentence template; the first letter is capitalized."""
        text = self.templates[key].format(**slots)
        text = _AFTER_STOP.sub(lambda m: m.group(1) + m.group(2).upper(), text)
        return text[:1].upper() + text[1:]

    def join(self, items: list[str]) -> str:
        if len(items) <= 1:
            return "".join(items)
        return self.list_separator.join(items[:-1]) + self.list_last + items[-1]


def _lexeme(concept: str, data: Mapping[str, Any]) -> Lexeme:
    return Lexeme(
        concept=concept,
        lemma=data["lemma"],
        domain=data.get("domain", "general"),
        level=int(data.get("level", 0)),
        gender=data.get("gender", "m"),
        plural=data.get("plural", ""),
        gloss=data.get("gloss", ""),
        pred=data.get("pred", ""),
        mass=bool(data.get("mass", False)),
        proper=bool(data.get("proper", False)),
        aliases=tuple(data.get("aliases", ())),
        adj=data.get("adj", ""),
        use=data.get("use", ""),
    )


def load_pack(code: str) -> LanguagePack:
    """Build a pack. The lexicon is a fresh object: learning never leaks between sessions."""
    raw = _raw(code)
    grammar, intents, style = raw["grammar.json"], raw["intents.json"], raw["style.json"]
    morphology: Morphology = _MORPHOLOGY[code](grammar["pred_fallback"])
    lexemes = (_lexeme(c, d) for c, d in sorted(raw["lexicon.json"]["concepts"].items()))
    return LanguagePack(
        code=code,
        lexicon=Lexicon(code, morphology, lexemes),
        templates=grammar["templates"],
        list_separator=grammar["list_separator"],
        list_last=grammar["list_last"],
        intents=tuple((name, re.compile(p)) for name, p in intents["intents"]),
        articles=tuple(sorted(intents["articles"], key=lambda a: (-len(a), a))),
        pronouns=frozenset(intents["pronouns"]),
        stopwords=frozenset(intents["stopwords"]),
        personal_markers=frozenset(intents["personal_markers"]),
        level_signals={k: re.compile(v) for k, v in intents["level_signals"].items()},
        level_only=re.compile(intents["level_only"]),
        style=StyleRules(
            rules=tuple(
                (cat, tuple(re.compile(p) for p in pats)) for cat, pats in style["rules"].items()
            ),
            waivers={k: re.compile(v) for k, v in style["waivers"].items()},
        ),
        greeting_prefix=re.compile(intents["greeting_prefix"]),
        laughter=re.compile(intents["laughter"]),
        filler=re.compile(intents["filler"]),
        operators=intents["operators"],
        arith_prefix=re.compile(intents["arith_prefix"]),
        weekdays=tuple(intents["weekdays"]),
        months=tuple(intents["months"]),
        negations=frozenset(intents["negations"]),
        negative_prefixes=tuple(intents["negative_prefixes"]),
        letter_confirm=re.compile(intents["letter_confirm"]),
        vowels=intents["vowels"],
        languages=intents["languages"],
        language_names=intents["language_names"],
        continuers=frozenset(intents["continuers"]),
        disambiguation=re.compile(intents["disambiguation"]),
    )
