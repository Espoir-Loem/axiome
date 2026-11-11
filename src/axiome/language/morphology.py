"""Inflection rules (articles, plurals, contractions) for each supported language.

Format specs understood by :meth:`form` (used in grammar templates):

``bare``    lemma                       chat / cat
``def``     definite                    le chat, l'arbre / the cat
``indef``   indefinite                  un chat / a cat, an array
``gen``     generic subject             le chat / a cat, length
``pl``      plural                      chats / cats
``def_pl``  definite plural             les chats / the cats
``de_pl``   "of" + bare plural          de chats, d'arbres / cats
``of_def``  "of" + definite             du temps, de la masse, de l'énergie / of the cat, of length
``pred``    property as a verb phrase   allaite ses petits / feeds its young
"""

from __future__ import annotations

import re

from axiome.language.lexicon import Lexeme
from axiome.perception.normalize import fold

_FR_VOWEL_START = re.compile(r"^[aeiouyh]")
_EN_VOWEL_LETTER_NAMES = frozenset("aefhilmnorsx")  # "an SI unit", "an HTML page"
_WORD_ACRONYM = 4  # SOLID, FIFO: long acronyms with a vowel are read as words


class French:
    def __init__(self, pred_fallback: str) -> None:
        self.pred_fallback = pred_fallback

    @staticmethod
    def _plural_word(word: str) -> str:
        w = fold(word)
        if w.endswith(("s", "x", "z")):
            return word
        if w.endswith(("eau", "au", "eu")):
            return word + "x"
        if w.endswith("al") and w not in {"bal", "carnaval", "festival", "chacal", "recital"}:
            return word[:-2] + "aux"
        return word + "s"

    def plural(self, lexeme: Lexeme) -> str:
        if lexeme.plural:
            return lexeme.plural
        head, sep, rest = lexeme.lemma.partition(" ")
        return self._plural_word(head) + sep + rest

    @staticmethod
    def _elides(word: str) -> bool:
        return bool(_FR_VOWEL_START.match(fold(word)))

    def form(self, lexeme: Lexeme, spec: str) -> str:
        lemma = lexeme.lemma
        feminine = lexeme.gender == "f"
        if lexeme.proper and spec in ("def", "gen", "indef"):  # "Félix", not "le Félix"
            return lemma
        if spec in ("def", "gen"):
            if self._elides(lemma):
                return f"l'{lemma}"
            return f"{'la' if feminine else 'le'} {lemma}"
        if spec == "indef":
            return f"{'une' if feminine else 'un'} {lemma}"
        if spec == "pl":
            return self.plural(lexeme)
        if spec == "def_pl":
            return f"les {self.plural(lexeme)}"
        if spec == "de_pl":
            pl = self.plural(lexeme)
            return f"d'{pl}" if self._elides(pl) else f"de {pl}"
        if spec == "of_def":
            if self._elides(lemma):
                return f"de l'{lemma}"
            return f"de la {lemma}" if feminine else f"du {lemma}"
        if spec == "pred":
            return lexeme.pred or self.pred_fallback.format(lemma=lemma)
        return lemma


class English:
    def __init__(self, pred_fallback: str) -> None:
        self.pred_fallback = pred_fallback

    @staticmethod
    def _plural_word(word: str) -> str:
        w = word.lower()
        if w.endswith(("s", "x", "z", "ch", "sh")):
            return word + "es"
        if len(w) > 1 and w.endswith("y") and w[-2] not in "aeiou":
            return word[:-1] + "ies"
        return word + "s"

    def plural(self, lexeme: Lexeme) -> str:
        if lexeme.plural:
            return lexeme.plural
        if lexeme.mass:
            return lexeme.lemma
        head, sep, last = lexeme.lemma.rpartition(" ")
        return head + sep + self._plural_word(last)

    @staticmethod
    def _article(lemma: str) -> str:
        first = lemma.split(" ", 1)[0]
        spelled = len(first) < _WORD_ACRONYM or not any(c in "AEIOU" for c in first)
        if len(first) > 1 and first.isupper() and spelled:  # initialism: read letter by letter
            return "an" if first[0].lower() in _EN_VOWEL_LETTER_NAMES else "a"
        return "an" if first[:1].lower() in "aeiou" else "a"

    def form(self, lexeme: Lexeme, spec: str) -> str:
        lemma = lexeme.lemma
        bare = lexeme.mass or lexeme.proper
        if spec == "def":
            return lemma if bare else f"the {lemma}"
        if spec in ("indef", "gen"):
            return lemma if bare else f"{self._article(lemma)} {lemma}"
        if spec in ("pl", "de_pl"):
            return self.plural(lexeme)
        if spec == "def_pl":
            return f"the {self.plural(lexeme)}"
        if spec == "of_def":
            return f"of {lemma}" if bare else f"of the {lemma}"
        if spec == "pred":
            return lexeme.pred or self.pred_fallback.format(lemma=lemma)
        return lemma
