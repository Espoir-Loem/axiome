"""Analyst: understands what the user wants.

Checklist: detect explicit level requests and style waivers, find the intent,
resolve every mention to a concept (or flag it unknown / ambiguous), resolve
pronouns and follow-ups against the conversation context, and measure how
technical the user's wording is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from axiome.dialogue.level import Level
from axiome.language.lexicon import GENERAL_DOMAIN
from axiome.language.pack import LanguagePack
from axiome.perception.normalize import fold, squash, words

SHORT_PHRASE = 4  # an unmatched message of at most this many words is read as a topic
MEANINGFUL_WORD = 2  # a message with no word of at least this many letters is incomplete
CONSONANT_RUN = 6  # a word with this many consonants in a row is keyboard noise ("asdfghjkl")
_ARITH = re.compile(r"[\d\s+\-*/^%().,]+")
_OPERATOR = re.compile(r"\d\s*[+\-*/^%]\s*[\d(]|\d\s*\^")
_CONSONANTS = re.compile(r"[bcdfghjklmnpqrstvwxz]+")


def _letters(text: str) -> int:
    return sum(c.isalnum() for c in text)


class Intent(Enum):
    GREETING = "greeting"
    THANKS = "thanks"
    FAREWELL = "farewell"
    IDENTITY = "identity"
    CAPABILITIES = "capabilities"
    CONFUSION = "confusion"
    LEVEL = "level"
    PROPERTIES = "properties"
    UNIT = "unit"
    COMPLEXITY = "complexity"
    MEMBERS = "members"
    CHECK_IS_A = "check_is_a"
    DEFINITION = "definition"
    RESEARCH = "research"
    FOLLOW_UP = "follow_up"
    TEACH_IS_A = "teach_is_a"
    HOW_ARE_YOU = "how_are_you"
    USER_FINE = "user_fine"
    NAME = "name"
    USER_NAME = "user_name"
    ACK = "ack"
    CHAT = "chat"  # addressed to Axiome but not understood: never a web search
    INCOMPLETE = "incomplete"  # nothing meaningful to work on ("h", "?")
    SINGLE_LETTER = "single_letter"  # topic is one letter: the letter itself, or a cut question
    ASK_USER_NAME = "ask_user_name"
    IDENTITY_AI = "identity_ai"
    HELP = "help"
    DATE = "date"
    CLOCK = "clock"
    FORECAST = "forecast"
    CODE_REQUEST = "code_request"
    PURPOSE = "purpose"
    COMPARE = "compare"
    WHY_IS_A = "why_is_a"
    WHY = "why"
    WHO = "who"
    CHECK_PROPERTY = "check_property"
    REQUIREMENTS = "requirements"
    ARITHMETIC = "arithmetic"
    LAUGHTER = "laughter"
    FILLER = "filler"
    GIBBERISH = "gibberish"
    LIMITS = "limits"
    UNKNOWN = "unknown"


TOPICAL = frozenset(
    {
        Intent.PROPERTIES,
        Intent.UNIT,
        Intent.COMPLEXITY,
        Intent.MEMBERS,
        Intent.DEFINITION,
        Intent.RESEARCH,
        Intent.WHO,
        Intent.WHY,
    }
)


@dataclass(frozen=True, slots=True)
class Mention:
    text: str  # the user's own words (original spelling)
    concepts: tuple[str, ...]  # candidates; empty when unknown
    pronoun: bool = False
    article: str = ""  # article the user put before the word (gives its gender)
    corrected: bool = False  # resolved through a typo correction

    @property
    def concept(self) -> str | None:
        return self.concepts[0] if len(self.concepts) == 1 else None

    @property
    def ambiguous(self) -> bool:
        return len(self.concepts) > 1


@dataclass(frozen=True, slots=True)
class Analysis:
    intent: Intent
    subject: Mention | None = None
    obj: Mention | None = None
    level: Level | None = None  # explicit request in this message
    waivers: frozenset[str] = frozenset()
    technical_terms: int = 0
    domain: str = GENERAL_DOMAIN
    detail: str = ""  # extra slot: arithmetic expression, property adjective, need...


@dataclass
class Context:
    """What the conversation is about (updated by the session after each turn)."""

    topic: Mention | None = None
    intent: Intent | None = None
    history: list[str] = field(default_factory=list)
    expect: str = ""  # what Axiome just asked for ("user_name"), valid for one turn


def _cut(orig: str, folded: str, pattern: re.Pattern[str]) -> tuple[str, str]:
    """Remove every match of ``pattern`` (found on ``folded``) from both strings."""
    spans = [m.span() for m in pattern.finditer(folded)]
    for start, end in reversed(spans):
        orig, folded = orig[:start] + orig[end:], folded[:start] + folded[end:]
    return orig, folded


def _tidy(orig: str, folded: str) -> tuple[str, str]:
    """Squash spaces and drop leftover separators, keeping both strings aligned."""
    keep = [
        i for i, c in enumerate(folded) if not (c.isspace() and (i == 0 or folded[i - 1].isspace()))
    ]
    orig, folded = "".join(orig[i] for i in keep), "".join(folded[i] for i in keep)
    strip = " ,;:"
    left = len(folded) - len(folded.lstrip(strip))
    right = len(folded.rstrip(strip))
    orig, folded = orig[left:right], folded[left:right]
    folded = re.sub(r" ([?!.])$", r"\1", folded)
    orig = re.sub(r" ([?!.])$", r"\1", orig)
    return orig, folded


def _gibberish(folded: str) -> bool:
    tokens = words(folded)
    return len(tokens) == 1 and any(
        len(run) >= CONSONANT_RUN for run in _CONSONANTS.findall(tokens[0])
    )


class Analyst:
    def __init__(self, pack: LanguagePack) -> None:
        self.pack = pack

    def _strip_article(self, orig: str, folded: str) -> tuple[str, str, str]:
        for article in self.pack.articles:
            glue = "" if article.endswith("'") else " "
            prefix = article + glue
            if folded.startswith(prefix) and len(folded) > len(prefix):
                return orig[len(prefix) :], folded[len(prefix) :], article
        return orig, folded, ""

    def resolve(self, orig: str, folded: str, context: Context) -> Mention:
        orig, folded = orig.strip(" ?.!"), folded.strip(" ?.!")
        if folded in self.pack.pronouns:
            if context.topic is not None:
                return context.topic
            return Mention(orig, (), pronoun=True)
        orig, folded, article = self._strip_article(orig, folded)
        found = self.pack.lexicon.lookup(folded)
        if found:
            return Mention(orig, found, article=article)
        guess = self.pack.lexicon.closest(folded)
        return Mention(orig, guess, article=article, corrected=bool(guess))

    def _valid(self, intent: Intent, m: re.Match[str], context: Context) -> bool:
        """Some patterns are too broad on their own: check that the words make sense."""
        if intent is Intent.CHECK_PROPERTY:
            return self.pack.lexicon.adjective(m["p"]) is not None
        if intent is Intent.WHY_IS_A:
            return all(
                self.resolve(m[g], m[g], context).concepts or m[g] in self.pack.pronouns
                for g in ("x", "y")
            )
        return True

    def arithmetic(self, folded: str) -> str | None:
        """The expression if the message is a calculation ("combien font 2 + 2 ?")."""
        text = self.pack.arith_prefix.sub("", folded.strip()).rstrip(" ?!=.")
        for spoken in sorted(self.pack.operators, key=lambda w: (-len(w), w)):
            text = re.sub(rf"\b{re.escape(spoken)}\b", f" {self.pack.operators[spoken]} ", text)
        text = " ".join(text.split())
        if text and _ARITH.fullmatch(text) and _OPERATOR.search(text):
            return text
        return None

    def _match(
        self, folded: str, context: Context | None = None
    ) -> tuple[Intent, re.Match[str] | None]:
        ctx = context or Context()
        for name, pattern in self.pack.intents:
            m = pattern.search(folded)
            if m and self._valid(Intent(name), m, ctx):
                return Intent(name), m
        tokens = words(folded)
        if self.pack.personal_markers.intersection(tokens):
            return Intent.CHAT, None
        if _gibberish(folded) and not self.pack.lexicon.lookup(folded.strip(" ?.!")):
            return Intent.GIBBERISH, None
        if folded.strip(" ?.!") and len(tokens) <= SHORT_PHRASE:
            return Intent.DEFINITION, None
        return Intent.UNKNOWN, None

    def _mentions(
        self,
        intent: Intent,
        match: re.Match[str] | None,
        orig: str,
        folded: str,
        context: Context,
    ) -> tuple[Mention | None, Mention | None]:
        groups = match.groupdict() if match is not None else {}
        subject = obj = None
        if match is not None and groups.get("n"):
            subject = Mention(orig[match.start("n") : match.end("n")], ())
        elif match is not None and "x" in groups:
            subject = self.resolve(orig[match.start("x") : match.end("x")], match["x"], context)
        elif intent in (Intent.DEFINITION, Intent.GIBBERISH):
            subject = self.resolve(orig, folded, context)
        elif intent is Intent.WHY:
            subject = Mention(orig.strip(" ?.!"), ())
        if match is not None and groups.get("y"):
            obj = self.resolve(orig[match.start("y") : match.end("y")], match["y"], context)
            if groups.get("ya") and not obj.article:
                obj = Mention(obj.text, obj.concepts, obj.pronoun, match["ya"].strip())
        return subject, obj

    def _shortcut(self, folded: str, waivers: frozenset[str]) -> Analysis | None:
        """Messages recognized as a whole: a calculation, a laugh, a hesitation."""
        expression = self.arithmetic(folded)
        if expression is not None:
            return Analysis(Intent.ARITHMETIC, waivers=waivers, detail=expression)
        for intent, pattern in (
            (Intent.LAUGHTER, self.pack.laughter),
            (Intent.FILLER, self.pack.filler),
        ):
            if pattern.fullmatch(folded):
                return Analysis(intent, waivers=waivers)
        return None

    def _classify(
        self, orig: str, folded: str, level: Level | None, context: Context
    ) -> tuple[Intent, re.Match[str] | None, str, str]:
        if level is not None and self.pack.level_only.fullmatch(folded.strip()):
            return Intent.LEVEL, None, orig, folded
        intent, match = self._match(folded, context)
        if intent is Intent.UNKNOWN and ", " in folded:  # "context..., actual question?"
            cut = folded.rindex(", ") + 2
            orig, folded = orig[cut:], folded[cut:]
            intent, match = self._match(folded, context)
        if match is None and context.expect == "user_name" and 0 < len(words(folded)) <= 2:
            name = orig.strip(" ?.!")  # the answer to "what's your name?"
            return Intent.USER_NAME, re.match(r"(?P<n>.+)", name), name, name
        return intent, match, orig, folded

    def analyze(self, text: str, context: Context) -> Analysis:
        orig = squash(text)
        folded = squash(fold(text))
        waivers = frozenset(c for c, p in self.pack.style.waivers.items() if p.search(folded))
        level: Level | None = None
        for name, signal in sorted(self.pack.level_signals.items()):
            if signal.search(folded):
                level = Level.BEGINNER if name == "beginner" else Level.EXPERT
                orig, folded = _cut(orig, folded, signal)
        orig, folded = _tidy(orig, folded)
        shortcut = self._shortcut(folded, waivers)
        if shortcut is not None:
            return shortcut
        greeting = self.pack.greeting_prefix.match(folded)
        if greeting is not None:  # "salut, ça va ?": answer the question
            orig, folded = orig[greeting.end() :], folded[greeting.end() :]
        intent, match, orig, folded = self._classify(orig, folded, level, context)
        subject, obj = self._mentions(intent, match, orig, folded, context)
        if intent is not Intent.LEVEL and not any(
            len(w) >= MEANINGFUL_WORD for w in words(fold(text))
        ):
            intent, subject, obj = Intent.INCOMPLETE, None, None
        elif intent in TOPICAL and subject is not None and _letters(subject.text) == 1:
            intent = Intent.SINGLE_LETTER
        if intent is Intent.FOLLOW_UP:
            intent = context.intent if context.intent in TOPICAL else Intent.DEFINITION

        lexicon = self.pack.lexicon
        own = set(subject.concepts if subject else ()) | set(obj.concepts if obj else ())
        technical = {
            c
            for c in lexicon.scan(text)
            if c not in own and (lx := lexicon.get(c)) is not None and lx.level >= 1
        }
        domain = GENERAL_DOMAIN
        focus = subject.concept if subject else None
        if focus is None and context.topic is not None:
            focus = context.topic.concept
        if focus is not None:
            domain = lexicon.lexeme(focus).domain
        detail = ""
        if match is not None:
            detail = match.groupdict().get("p") or match.groupdict().get("q") or ""
            if intent is Intent.PURPOSE:
                detail = match["x"]
                subject = None
        return Analysis(intent, subject, obj, level, waivers, len(technical), domain, detail)
