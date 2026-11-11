"""A tiny Wikidata, served through the fetcher interface (no network)."""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping

from axiome.perception.normalize import fold

# qid: (fr, en, fr description, P279, P31, P171)
ITEMS: dict[str, tuple[str, str, str, list[str], list[str], list[str]]] = {
    "Q1": ("trou noir", "black hole", "objet céleste très compact", ["Q2"], ["Q9"], []),
    "Q2": ("objet céleste", "astronomical object", "", [], [], []),
    "Q9": ("type d'objet astronomique", "type of astronomical object", "", [], [], []),
    "Q3": ("lion", "lion", "espèce de félins", [], ["Q16521"], ["Q4"]),
    "Q4": ("Panthera", "Panthera", "", [], ["Q16521"], ["Q5"]),
    "Q5": ("félidés", "Felidae", "", [], ["Q16521"], ["Q6"]),
    "Q6": ("mammifères", "mammal", "", [], ["Q16521"], []),
    "Q7": ("mammifère", "mammal", "", [], [], []),
    "Q8": ("Lion", "Leo", "", [], ["Q4167410"], []),
    "Q10": ("naine jaune", "yellow dwarf", "étoile", ["Q11", "Q12"], [], []),
    "Q11": ("étoile", "star", "", [], [], []),
    "Q12": ("dark thing", "dark thing", "", [], [], []),  # untranslated: never used
    "Q13": ("Marie Curie", "Marie Curie", "physicienne", [], ["Q5"], []),
    "Q5000": ("être humain", "human", "", [], [], []),
}
LEXEMES = {"trou": "Q499327", "objet": "Q499327", "etoile": "Q1775415", "lion": "Q499327"}


def _claims(**props: list[str]) -> dict[str, list[dict[str, object]]]:
    return {
        p: [{"rank": "normal", "mainsnak": {"datavalue": {"value": {"id": v}}}} for v in vs]
        for p, vs in props.items()
        if vs
    }


class FakeWikidata:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, url: str, headers: Mapping[str, str] | None = None) -> bytes:
        self.calls.append(url)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if q["action"] == "wbsearchentities":
            return json.dumps(self._search(q)).encode()
        return json.dumps(self._entities(q["ids"].split("|"))).encode()

    def _search(self, q: dict[str, str]) -> dict[str, object]:
        text, lang = fold(q["search"]), q["language"]
        if q["type"] == "lexeme":
            ids = [f"L{i}" for i, w in enumerate(LEXEMES) if w == text]
            hits = [
                {
                    "id": lid,
                    "label": q["search"],
                    "description": "French, noun",
                    "match": {"language": lang, "text": q["search"]},
                }
                for lid in ids
            ]
            return {"search": hits}
        hits = []
        for qid, (fr, en, *_rest) in ITEMS.items():
            for label in (fr, en):
                if fold(label) == text:
                    hits.append({"id": qid, "match": {"text": label}})
                    break
        hits.sort(key=lambda h: str(h["match"]["text"]) == q["search"])  # wrong case first
        return {"search": hits}

    def _entities(self, ids: list[str]) -> dict[str, object]:
        out: dict[str, object] = {}
        words = list(LEXEMES)
        for qid in ids:
            if qid.startswith("L"):
                out[qid] = {"claims": _claims(P5185=[LEXEMES[words[int(qid[1:])]]])}
            elif qid in ITEMS:
                fr, en, desc, sub, inst, taxon = ITEMS[qid]
                out[qid] = {
                    "labels": {"fr": {"value": fr}, "en": {"value": en}},
                    "descriptions": {"fr": {"value": desc}} if desc else {},
                    "claims": _claims(P279=sub, P31=inst, P171=taxon),
                }
            else:
                out[qid] = {"missing": ""}
        return {"entities": out}
