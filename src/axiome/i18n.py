"""Internationalisation: every user-facing string lives in ``axiome/locales/*.json``.

Source code never embeds display text. It builds :class:`Msg` values (a key plus
parameters) that are rendered lazily in the active locale, so the same reasoning
trace can be displayed in any supported language.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import cache
from importlib import resources

SUPPORTED = ("en", "fr")
DEFAULT = "fr"
_state = {"locale": os.environ.get("AXIOME_LANG", DEFAULT)}


@cache
def _catalog(locale: str) -> dict[str, str]:
    text = resources.files("axiome.locales").joinpath(f"{locale}.json").read_text("utf-8")
    data: dict[str, str] = json.loads(text)
    return data


def set_locale(locale: str) -> None:
    if locale not in SUPPORTED:
        raise ValueError(f"unsupported locale {locale!r}; expected one of {SUPPORTED}")
    _state["locale"] = locale


def get_locale() -> str:
    locale = _state["locale"]
    return locale if locale in SUPPORTED else DEFAULT


def t_in(locale: str, key: str, **params: object) -> str:
    """Translate ``key`` in ``locale`` (falls back to English, then to the key)."""
    locale = locale if locale in SUPPORTED else DEFAULT
    template = _catalog(locale).get(key) or _catalog("en").get(key) or key
    rendered = {k: v.render(locale) if isinstance(v, Msg) else str(v) for k, v in params.items()}
    return template.format(**rendered)


def t(key: str, **params: object) -> str:
    """Translate ``key`` in the active locale (falls back to English, then to the key)."""
    return t_in(get_locale(), key, **params)


@dataclass(frozen=True, slots=True)
class Msg:
    """A translatable message. Hashable and comparable, hence safe in frozen data."""

    key: str
    params: tuple[tuple[str, object], ...] = ()

    def __str__(self) -> str:
        return t(self.key, **dict(self.params))

    def render(self, locale: str) -> str:
        return t_in(locale, self.key, **dict(self.params))


def msg(key: str, **params: object) -> Msg:
    return Msg(key, tuple(sorted(params.items())))
