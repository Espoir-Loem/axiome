"""Held-out generation bench built from real commits (M7.5).

The curated bench (``evals/code/generation.jsonl``) was written alongside the
search, so it mostly proves the harness works. This bench is built the other way
round: each case replays a real commit of this repository.

The search starts from the parent tree, sees the project's tests as they exist
in the fixing commit, and must make them pass. Two properties keep the measure
honest:

* the tests must fail before any mutation, so a case that is already green is an
  integrity error rather than a free success;
* the expected patch is never read here, so ``pass@1`` measures generalisation,
  not the reproduction of a curated answer.

Only the test files of the fixing commit are overlaid; the search may edit one
target file, while the real fix may have touched more (``changed`` records all
of them). That gap is part of what the bench measures.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from axiome.code.generate import ACCEPTED, generate
from axiome.code.sandbox import run_tests
from axiome.core.errors import CodeError

DEFAULT_BUDGET = 4


@dataclass(frozen=True, slots=True)
class HeldoutCase:
    """One real commit to replay."""

    id: str
    commit: str
    parent: str
    target: str
    tests: tuple[str, ...]
    changed: tuple[str, ...]
    summary: str


@dataclass(frozen=True, slots=True)
class HeldoutOutcome:
    """What the bounded search did on one case."""

    case: HeldoutCase
    status: str
    attempts: int

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTED


@dataclass(frozen=True, slots=True)
class HeldoutReport:
    """Aggregate score of the held-out bench."""

    outcomes: tuple[HeldoutOutcome, ...]

    @property
    def cases(self) -> int:
        return len(self.outcomes)

    @property
    def accepted(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.accepted)

    @property
    def pass_at_1(self) -> float:
        return self.accepted / self.cases if self.cases else 0.0


def load_heldout(path: str | Path) -> tuple[HeldoutCase, ...]:
    """Read the bench file; every case must name a commit, its parent and a target."""
    with Path(path).open(encoding="utf-8") as handle:
        return tuple(
            HeldoutCase(
                str(row["id"]),
                str(row["commit"]),
                str(row["parent"]),
                str(row["target"]),
                _strings(row["tests"]),
                _strings(row["changed"]),
                str(row["summary"]),
            )
            for row in _lines(handle)
        )


def run_heldout(
    cases: Sequence[HeldoutCase],
    repository: str | Path,
    *,
    budget: int = DEFAULT_BUDGET,
    isolate_network: bool = False,
) -> HeldoutReport:
    """Replay every case: materialise the parent tree, check it fails, then search."""
    repo = Path(repository)
    outcomes: list[HeldoutOutcome] = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="axiome-heldout-") as temporary:
            root = Path(temporary)
            _materialise(repo, case, root)
            before = run_tests(root, case.tests, isolate_network=isolate_network)
            if before.passed:
                raise CodeError("code.heldout_not_failing", id=case.id)
            result = generate(
                root,
                case.target,
                case.tests,
                budget=budget,
                isolate_network=isolate_network,
            )
        outcomes.append(HeldoutOutcome(case, result.status, len(result.attempts)))
    return HeldoutReport(tuple(outcomes))


def _materialise(repo: Path, case: HeldoutCase, root: Path) -> None:
    """Extract the parent tree, then overlay the tests of the fixing commit."""
    payload = _git(repo, "archive", case.parent)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        _extract(archive, root)
    for test in case.tests:
        destination = root / test
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_git(repo, "show", f"{case.commit}:{test}"))


def _extract(archive: tarfile.TarFile, root: Path) -> None:
    """Write regular files only, refusing any member outside ``root``."""
    base = root.resolve()
    for member in archive.getmembers():
        if not member.isfile():
            continue
        destination = (root / member.name).resolve()
        if not destination.is_relative_to(base):
            raise CodeError("code.outside_repository", path=member.name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = archive.extractfile(member)
        if payload is not None:
            destination.write_bytes(payload.read())


def _git(repo: Path, *arguments: str) -> bytes:
    """Read objects from the local repository; never executes project code."""
    command = ["git", "-C", str(repo), *arguments]
    try:
        return subprocess.run(command, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CodeError("code.heldout_history", detail=str(exc)) from exc


def _lines(handle: Iterator[str] | Sequence[str]) -> Iterator[dict[str, object]]:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("expected a JSON object")
            yield row


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("expected a JSON array")
    return tuple(str(item) for item in value)
