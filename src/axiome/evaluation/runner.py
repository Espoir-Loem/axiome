"""Runs evaluation suites the way a model release is evaluated.

A suite is a JSONL file; each line is one case:

    {"id": "smalltalk-fr-001", "category": "smalltalk", "lang": "fr",
     "setup": ["je m'appelle Espoir"],            # turns played before, not graded
     "turn": "salut",                              # the graded turn
     "expect": {"contains": ["Espoir"], "no_search": true}}

Checks (all optional, all must pass): ``contains`` / ``not_contains`` (accent and
case insensitive), ``any_of``, ``starts_with``, ``equals``, ``no_search``,
``searches``, ``max_chars``. Two checks always apply: no AI tell
(``docs/signes-ia.md``) and no crash. Web research uses recorded documents
(``evals/fixtures/web.json``), so a run is deterministic and offline.
"""

from __future__ import annotations

import json
import traceback
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from typing import Any

from axiome.core.clock import FixedClock
from axiome.dialogue.events import Say, Searching, Thinking
from axiome.dialogue.layout import render
from axiome.dialogue.session import Session
from axiome.kernel import Kernel
from axiome.perception.normalize import fold
from axiome.research.providers.base import Document
from axiome.team.researcher import Researcher
from axiome.verification.epistemic import Reliability, Source, SourceKind

EVAL_TIME = "2026-11-11T09:30:00+00:00"


class FixtureProvider:
    """A search provider answering from recorded documents.

    Records are keyed by folded query, optionally prefixed by a language code
    ("en:photon"); the language-specific record wins.
    """

    name = "Wikipedia"
    deep = False

    def __init__(self, records: dict[str, list[dict[str, str]]]) -> None:
        self.records = {fold(k): v for k, v in records.items()}

    def search(self, query: str, language: str, limit: int) -> list[Document]:
        out = []
        key = fold(query).strip(" ?.!")
        records = self.records.get(f"{language}:{key}", self.records.get(key, []))
        for rec in records[:limit]:
            url = rec["url"]
            source = Source(
                id=f"fixture:{url}",
                name=rec.get("name", f"Wikipedia ({language})"),
                kind=SourceKind.REFERENCE,
                reliability=Reliability[rec.get("reliability", "HIGH")],
                organization=rec.get("organization", "wikipedia.org"),
                url=url,
            )
            out.append(Document(source, rec["title"], rec["text"]))
        return out


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    category: str
    lang: str
    turn: str
    expect: dict[str, Any]
    setup: tuple[str, ...] = ()
    online: bool = True


@dataclass(frozen=True, slots=True)
class Outcome:
    case: Case
    answer: str
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass
class Report:
    outcomes: list[Outcome] = field(default_factory=list)

    def by_category(self) -> dict[str, tuple[int, int]]:
        total: Counter[str] = Counter()
        ok: Counter[str] = Counter()
        for o in self.outcomes:
            total[o.case.category] += 1
            ok[o.case.category] += o.passed
        return {c: (ok[c], total[c]) for c in sorted(total)}

    @property
    def score(self) -> tuple[int, int]:
        return sum(o.passed for o in self.outcomes), len(self.outcomes)

    def markdown(self) -> str:
        passed, total = self.score
        lines = [
            "# Rapport d'évaluation",
            "",
            f"Score global : **{passed}/{total}** ({(100 * passed) // max(1, total)} %)",
            "",
            "| Catégorie | Réussis | Total | % |",
            "|---|---|---|---|",
        ]
        for cat, (ok, n) in self.by_category().items():
            lines.append(f"| {cat} | {ok} | {n} | {(100 * ok) // n} |")
        failed = [o for o in self.outcomes if not o.passed]
        if failed:
            lines += ["", "## Échecs", ""]
            for o in failed:
                lines.append(f"### {o.case.id} ({o.case.lang})")
                lines.append(f"- Entrée : `{o.case.turn}`")
                lines.append(f"- Problèmes : {'; '.join(o.failures)}")
                shown = o.answer.replace("\n", " / ")[:400]
                lines.append(f"- Réponse : {shown}")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def load_cases(paths: Iterable[Path]) -> list[Case]:
    cases: list[Case] = []
    for path in sorted(paths):
        for n, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
            if not line.strip() or line.lstrip().startswith("//"):
                continue
            data = json.loads(line)
            try:
                cases.append(
                    Case(
                        id=data["id"],
                        category=data["category"],
                        lang=data["lang"],
                        turn=data["turn"],
                        expect=data.get("expect", {}),
                        setup=tuple(data.get("setup", ())),
                        online=data.get("online", True),
                    )
                )
            except KeyError as exc:  # pragma: no cover - authoring error
                raise ValueError(f"{path}:{n}: missing {exc}") from exc
    ids = [c.id for c in cases]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate case ids: {duplicates}")
    return cases


def _has(answer: str, needle: str) -> bool:
    return fold(needle) in fold(answer)


def grade(case: Case, answer: str, searched: bool, tells: Sequence[str]) -> list[str]:
    e = case.expect
    out: list[str] = []
    out += [f"manque « {s} »" for s in e.get("contains", []) if not _has(answer, s)]
    out += [f"contient « {s} »" for s in e.get("not_contains", []) if _has(answer, s)]
    if e.get("any_of") and not any(_has(answer, s) for s in e["any_of"]):
        out.append(f"aucun de {e['any_of']}")
    if "starts_with" in e and not fold(answer).startswith(fold(e["starts_with"])):
        out.append(f"ne commence pas par « {e['starts_with']} »")
    if "equals" in e and answer != e["equals"]:
        out.append(f"différent de « {e['equals']} »")
    if e.get("no_search") and searched:
        out.append("a lancé une recherche inutile")
    if e.get("searches") and not searched:
        out.append("n'a pas cherché")
    if "max_chars" in e and len(answer) > e["max_chars"]:
        out.append(f"trop long ({len(answer)} > {e['max_chars']})")
    out += [f"signe IA {t}" for t in tells]
    return out


def run_case(case: Case, records: dict[str, list[dict[str, str]]]) -> Outcome:
    kernel = Kernel.in_memory(FixedClock(EVAL_TIME))
    researcher = Researcher([FixtureProvider(records)]) if case.online else None
    session = Session(kernel, case.lang, researcher, timezone=timezone.utc)
    try:
        for turn in case.setup:
            list(session.respond(turn))
        events = list(session.respond(case.turn))
    except Exception:
        return Outcome(case, "", (f"plantage : {traceback.format_exc(limit=3)}",))
    answer = render(e for e in events if not isinstance(e, Thinking))
    searched = any(isinstance(e, Searching) for e in events)
    tells: list[str] = []
    for e in events:
        if isinstance(e, Say):
            tells += session.reviewer.style(e.text)[1]
    return Outcome(case, answer, tuple(grade(case, answer, searched, sorted(set(tells)))))


def run(suite_dir: Path, fixtures: Path) -> Report:
    records = json.loads(fixtures.read_text("utf-8")) if fixtures.exists() else {}
    report = Report()
    for case in load_cases(suite_dir.glob("*.jsonl")):
        report.outcomes.append(run_case(case, records))
    return report
