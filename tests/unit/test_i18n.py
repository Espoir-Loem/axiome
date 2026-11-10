"""Locale catalogs must be complete and consistent with the source code."""

from __future__ import annotations

import json
import re
import string
from importlib import resources
from pathlib import Path

import pytest

import axiome
from axiome.i18n import SUPPORTED, get_locale, msg, set_locale, t

SRC = Path(axiome.__file__).parent
KEY_CALL = re.compile(r"""\b(?:t|msg|Error)\(\s*["']([a-z_]+\.[A-Za-z_]+)["']""")


def catalog(lang: str) -> dict[str, str]:
    text = resources.files("axiome.locales").joinpath(f"{lang}.json").read_text("utf-8")
    data: dict[str, str] = json.loads(text)
    return data


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_catalogs_have_identical_keys_and_placeholders() -> None:
    en, fr = catalog("en"), catalog("fr")
    assert set(en) == set(fr)
    for key in en:
        assert placeholders(en[key]) == placeholders(fr[key]), key


def test_every_key_used_in_code_exists() -> None:
    used: set[str] = set()
    for path in SRC.rglob("*.py"):
        used |= set(KEY_CALL.findall(path.read_text("utf-8")))
    used |= {
        f"status.{s}"
        for s in (
            "REFUTED",
            "CONTESTED",
            "UNVERIFIED",
            "PLAUSIBLE",
            "CONFIRMED",
            "VERIFIED",
            "PROVED",
        )
    }
    missing = used - set(catalog("en"))
    assert not missing, missing


def test_translation_and_fallbacks() -> None:
    assert t("render.yes") == "Yes"
    set_locale("fr")
    assert t("render.yes") == "Oui"
    assert str(msg("tell.noted", atom="p(a)")) == "Noté : p(a)"
    assert t("no.such.key") == "no.such.key"
    set_locale("en")
    assert get_locale() == "en"
    with pytest.raises(ValueError):
        set_locale("xx")
    assert "en" in SUPPORTED
