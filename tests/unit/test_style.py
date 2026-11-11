"""Reviewer: zero-error rules R1-R3 and the AI-tell style gate (docs/signes-ia.md)."""

from __future__ import annotations

import json
from importlib import resources

import pytest

from axiome.language.pack import load_pack
from axiome.team.reviewer import Reviewer
from axiome.team.writer import Claim
from axiome.verification.epistemic import Status

FR = Reviewer(load_pack("fr"))
EN = Reviewer(load_pack("en"))


@pytest.mark.parametrize(
    ("reviewer", "text", "expected", "category"),
    [
        (FR, "Excellente question ! Le chat est un mammifère.", "Le chat est un mammifère.", "S1"),
        (FR, "Bien sûr ! Le chat est un mammifère.", "Le chat est un mammifère.", "S1"),
        (FR, "Le chat miaule. N'hésitez pas à me demander.", "Le chat miaule.", "S3"),
        (FR, "Il est important de noter que le chat dort.", "Le chat dort.", "S4"),
        (FR, "Le chat dort 😺.", "Le chat dort.", "S5"),
        (FR, "Le chat — un félin — dort.", "Le chat, un félin, dort.", "S5"),
        (FR, "Le chat dort. Désolé pour la confusion.", "Le chat dort.", "S6"),
        (FR, "Le chat dort. Veux-tu un exemple ?", "Le chat dort.", "S7"),
        (EN, "Great question! A cat is a mammal.", "A cat is a mammal.", "S1"),
        (EN, "A cat is a mammal. I hope this helps!", "A cat is a mammal.", "S3"),
        (EN, "Let's dive into cats. Cats sleep.", "Cats sleep.", "S4"),
        (EN, "Cats sleep. Would you like me to explain more?", "Cats sleep.", "S7"),
    ],
)
def test_ai_tells_are_removed(reviewer: Reviewer, text: str, expected: str, category: str) -> None:
    cleaned, fired = reviewer.style(text)
    assert cleaned == expected
    assert category in fired


def test_self_reference_blocks_and_waivers_lift() -> None:
    assert FR.style("En tant qu'IA, je pense que oui.")[0] is None
    assert EN.style("As an AI language model, I think so.")[0] is None
    assert FR.style("Le chat dort 😺.", frozenset({"S5"}))[0] == "Le chat dort 😺."
    assert FR.style("Le chat dort.") == ("Le chat dort.", [])
    assert FR.style("En résumé, le chat dort.")[0] == "En résumé, le chat dort."
    assert FR.style("Le **chat** dort. [1]") == ("Le **chat** dort. [1]", [])  # structure is fine


def test_substance_rules() -> None:
    review = FR.review(
        [
            Claim("Fait sans source.", Status.PROVED),
            Claim("Fait faible.", Status.UNVERIFIED, ("a",)),
            Claim("Fait couvert sans note.", Status.PLAUSIBLE, ("a",), covered=True),
            Claim("Fait réfuté.", Status.REFUTED, ("a",)),
            Claim("Non vérifié : fait faible.", Status.UNVERIFIED, ("a",), hedged=True),
            Claim("Fait solide.", Status.PROVED, ("a",)),
            Claim("Bonjour.", factual=False),
            Claim("En tant qu'IA, bonjour.", factual=False),
            Claim("😺", factual=False),
            Claim("Excellente question ! Bonjour.", factual=False),
        ]
    )
    assert [rule for _, rule in review.blocked] == ["R1", "R2", "R2", "R3", "S2", "empty"]
    noted = FR.review(
        [
            Claim("Fait couvert.", Status.PLAUSIBLE, ("a",), covered=True),
            Claim("Note.", role="note", factual=False),
        ]
    )
    assert not noted.blocked
    assert [c.text for c in review.approved] == [
        "Non vérifié : fait faible.",
        "Fait solide.",
        "Bonjour.",
        "Bonjour.",
    ]
    assert review.corrected == 1


@pytest.mark.parametrize("code", ["fr", "en"])
def test_no_template_contains_an_ai_tell(code: str) -> None:
    reviewer = Reviewer(load_pack(code))
    base = resources.files("axiome.data.lang").joinpath(code)
    templates = json.loads(base.joinpath("grammar.json").read_text("utf-8"))["templates"]
    for key, template in templates.items():
        text = template.replace("{", "").replace("}", "")
        assert reviewer.style(text)[1] == [], key
