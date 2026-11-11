"""Main-text extraction from HTML and sentence segmentation (standard library only)."""

from __future__ import annotations

import re
from html.parser import HTMLParser

SKIPPED = frozenset(
    {
        "script",
        "style",
        "noscript",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "svg",
        "button",
        "sup",
    }
)
BLOCKS = frozenset({"p", "li", "h1", "h2", "h3", "h4", "blockquote", "dd", "td", "div", "br"})
MIN_SENTENCE_CHARS = 25
MAX_SENTENCE_CHARS = 400
_ABBREVIATIONS = (
    "M.",
    "Mme.",
    "Dr.",
    "Pr.",
    "St.",
    "e.g.",
    "i.e.",
    "etc.",
    "vs.",
    "cf.",
    "p.",
    "env.",
)
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9«\"(])")
_SPACES = re.compile(r"\s+")
_BRACKETS = re.compile(r"\[\d+\]|\[note \d+\]")


class _MainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0  # inside skipped elements
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED:
            self.depth += 1
        elif tag in BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED and self.depth:
            self.depth -= 1
        elif tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.depth:
            self.parts.append(data)


def main_text(html: str) -> str:
    parser = _MainText()
    parser.feed(html)
    parser.close()
    blocks = ("".join(parser.parts)).split("\n")
    paragraphs = [_SPACES.sub(" ", b).strip() for b in blocks]
    return "\n".join(p for p in paragraphs if len(p) >= MIN_SENTENCE_CHARS)


def sentences(text: str) -> list[str]:
    """Split into sentences, keeping only those long enough to carry a claim."""
    text = _BRACKETS.sub("", text)
    protected = text
    for i, abbr in enumerate(_ABBREVIATIONS):
        protected = protected.replace(abbr, f"\x00{i}\x00")
    out: list[str] = []
    for paragraph in protected.split("\n"):
        for raw in _SPLIT.split(paragraph):
            s = raw
            for i, abbr in enumerate(_ABBREVIATIONS):
                s = s.replace(f"\x00{i}\x00", abbr)
            s = _SPACES.sub(" ", s).strip()
            if MIN_SENTENCE_CHARS <= len(s) <= MAX_SENTENCE_CHARS:
                out.append(s)
    return out
