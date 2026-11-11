"""Text normalization.

:func:`fold` is *length preserving*: character ``i`` of the folded text comes
from character ``i`` of the input. Patterns can therefore be matched on folded
text and their spans applied to the original text.
"""

from __future__ import annotations

import re
import unicodedata

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'"})
_WORD = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*'?")
_SPACES = re.compile(r"\s+")
_FINAL_PUNCT = re.compile(r"\s+([?!.]+)$")


def _fold_char(ch: str) -> str:
    base = unicodedata.normalize("NFKD", ch)
    head = base[0] if base else ch
    lowered = head.lower()
    return lowered if len(lowered) == 1 else ch


def fold(text: str) -> str:
    """Lowercase, strip diacritics and straighten apostrophes, keeping the length."""
    return "".join(_fold_char(c) for c in text.translate(_APOSTROPHES))


def squash(text: str) -> str:
    """Collapse whitespace and glue final punctuation (``"chat ?"`` -> ``"chat?"``)."""
    return _FINAL_PUNCT.sub(r"\1", _SPACES.sub(" ", text).strip())


def prepare(text: str) -> str:
    return squash(fold(text))


def words(text: str) -> list[str]:
    """Words of an already folded text (elided articles stay attached: ``l'``)."""
    return _WORD.findall(text)


def slug(text: str) -> str:
    """A bare logic identifier for a phrase (``"Le photon"`` -> ``"le_photon"``)."""
    tokens = re.findall(r"[a-z0-9]+", fold(text))
    if not tokens:
        return ""
    ident = "_".join(tokens)
    return ident if ident[0].isalpha() else f"n_{ident}"
