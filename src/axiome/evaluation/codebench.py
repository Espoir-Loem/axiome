"""Code benches: labelled diff review and execution-verified generation.

Separate from the conversation benches (``evals/code/``): review is scored
*per rule* (a global score would hide a rule that cries wolf), and generation
reports ``pass@1`` plus the rate of silently wrong patches, which must stay at
zero (RFC-0002).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from axiome.code.generate import generate
from axiome.code.review import review_diff


@dataclass(frozen=True, slots=True)
class ReviewCase:
    id: str
    files: Mapping[str, str]
    diff: str
    expect: tuple[tuple[str, str], ...]  # (rule, path)


@dataclass(frozen=True, slots=True)
class RuleScore:
    expected: int
    found: int
    hits: int

    @property
    def recall(self) -> float:
        return self.hits / self.expected if self.expected else 1.0

    @property
    def precision(self) -> float:
        return self.hits / self.found if self.found else 1.0


@dataclass(frozen=True, slots=True)
class ReviewReport:
    cases: int
    rules: Mapping[str, RuleScore]

    @property
    def perfect(self) -> bool:
        return all(score.recall == 1.0 and score.precision == 1.0 for score in self.rules.values())


@dataclass(frozen=True, slots=True)
class GenerationCase:
    id: str
    target: str
    files: Mapping[str, str]
    tests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationReport:
    cases: int
    accepted: int
    silent_failures: int  # announced correct by the bench but tests did not pass

    @property
    def pass_at_1(self) -> float:
        return self.accepted / self.cases if self.cases else 0.0


def _lines(path: Path) -> Iterator[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_review(path: str | Path) -> tuple[ReviewCase, ...]:
    return tuple(
        ReviewCase(
            str(row["id"]),
            {str(k): str(v) for k, v in _mapping(row["files"]).items()},
            str(row["diff"]),
            _pairs(row["expect"]),
        )
        for row in _lines(Path(path))
    )


def load_generation(path: str | Path) -> tuple[GenerationCase, ...]:
    return tuple(
        GenerationCase(
            str(row["id"]),
            str(row["target"]),
            {str(k): str(v) for k, v in _mapping(row["files"]).items()},
            tuple(str(test) for test in _sequence(row.get("tests", []))),
        )
        for row in _lines(Path(path))
    )


def run_review(cases: Sequence[ReviewCase]) -> ReviewReport:
    expected: dict[str, int] = {}
    found: dict[str, int] = {}
    hits: dict[str, int] = {}
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="axiome-bench-") as temporary:
            root = Path(temporary)
            for relative, text in case.files.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            diagnostics = review_diff(root, case.diff)
        actual = {(d.rule, d.path) for d in diagnostics}
        wanted = set(case.expect)
        for rule, _path in wanted:
            expected[rule] = expected.get(rule, 0) + 1
            hits[rule] = hits.get(rule, 0) + (1 if (rule, _path) in actual else 0)
        for rule, _path in actual:
            found[rule] = found.get(rule, 0) + 1
    names = sorted(set(expected) | set(found))
    scores = {
        name: RuleScore(expected.get(name, 0), found.get(name, 0), hits.get(name, 0))
        for name in names
    }
    return ReviewReport(len(cases), scores)


def run_generation(
    cases: Sequence[GenerationCase], *, budget: int = 12, isolate_network: bool = False
) -> GenerationReport:
    accepted = 0
    silent = 0
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="axiome-bench-") as temporary:
            root = Path(temporary)
            for relative, text in case.files.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            result = generate(
                root,
                case.target,
                case.tests,
                budget=budget,
                isolate_network=isolate_network,
            )
        if result.accepted:
            accepted += 1
        elif result.patch:
            silent += 1  # pragma: no cover - guarded by construction
    return GenerationReport(len(cases), accepted, silent)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _sequence(value: object) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError("expected a JSON array")
    return value


def _pairs(value: object) -> tuple[tuple[str, str], ...]:
    rows = _sequence(value)
    out: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("expected [rule, path] pairs")
        out.append((str(row[0]), str(row[1])))
    return tuple(out)
