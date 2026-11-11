"""Lays the event stream out as readable text, chunk by chunk.

The layout follows what a careful human writer does: the lead sentences form the
opening paragraph (the summary), details become a list, the reliability note and
the "see also" line form a closing paragraph, then the numbered sources. Bold is
written as Markdown, or as terminal bold when ``color`` is on.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from axiome.dialogue.events import Done, Event, Say, Thinking

BOLD, DIM, RESET = "\x1b[1m", "\x1b[2m", "\x1b[0m"
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE = frozenset({"lead", "social"})
CLOSING = frozenset({"note", "see_also"})


def _style(text: str, color: bool) -> str:
    return _MD_BOLD.sub(lambda m: f"{BOLD}{m.group(1)}{RESET}", text) if color else text


def chunks(events: Iterable[Event], *, color: bool = False) -> Iterator[str]:
    previous = ""  # role of the last sentence written ("" = nothing on the line yet)
    for event in events:
        if isinstance(event, Thinking):
            line = f"  {event.text}"
            yield ("\n" if previous else "") + (f"{DIM}{line}{RESET}" if color else line) + "\n"
            previous = ""
        elif isinstance(event, Say):
            role = event.role
            text = _style(event.text, color)
            if role in INLINE:
                same = previous == role or (previous == "lead" and role == "social")
                sep = " " if same else ("\n\n" if previous else "")
                yield sep + text
            elif role == "point":
                sep = "\n" if previous == "point" else ("\n\n" if previous else "")
                yield sep + "- " + text
            elif role in CLOSING:
                sep = "\n" if previous in CLOSING else ("\n\n" if previous else "")
                yield sep + text
            else:  # source
                sep = "\n" if previous == "source" else ("\n\n" if previous else "")
                yield sep + text
            previous = role
        elif isinstance(event, Done) and previous:
            yield "\n"


def render(events: Iterable[Event]) -> str:
    return "".join(chunks(events)).strip("\n")
