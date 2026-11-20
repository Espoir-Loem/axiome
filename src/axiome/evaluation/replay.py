"""Held-out replay bench on real commits (M7.6).

Each case replays a real commit of this repository, backwards. The tree of the
fixing commit is extracted, the source files it touched are restored to their
parent version, and the commit's tests are run: they must fail. Only then does
the bounded search get a chance to edit one target file and is it judged by the
same tests. The expected patch is never read. A manifest may also set ``depth`` and
``extra_targets`` to measure composed, multi-file searches; the shipped corpus
uses the defaults.

Two properties keep the measure honest:

* a case whose tests already pass is an integrity error, not a free success;
* the corpus keeps the real patch's shape (``changed`` lists every source file
  the commit touched), so a single-file search that cannot reproduce a
  multi-file fix is reported as a failure rather than hidden.

The corpus lives in ``evals/code/replay/``: one directory per case, a manifest,
and the parent versions of the reverted files. Adding a case is data only.
"""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from axiome.code.generate import ACCEPTED, generate
from axiome.code.sandbox import run_tests
from axiome.core.errors import CodeError

DEFAULT_BUDGET = 4


@dataclass(frozen=True, slots=True)
class ReplayCase:
    """One real commit, replayed backwards."""

    id: str
    commit: str
    target: str
    tests: tuple[str, ...]
    changed: tuple[str, ...]
    summary: str
    depth: int = 1
    extra_targets: tuple[str, ...] = ()
    files: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReplayOutcome:
    """What the bounded search did on one case."""

    case: ReplayCase
    status: str
    attempts: int

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTED


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """Aggregate score of the replay bench."""

    outcomes: tuple[ReplayOutcome, ...]

    @property
    def cases(self) -> int:
        return len(self.outcomes)

    @property
    def accepted(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.accepted)

    @property
    def multi_file(self) -> int:
        return sum(1 for outcome in self.outcomes if len(outcome.case.changed) > 1)

    @property
    def pass_at_1(self) -> float:
        return self.accepted / self.cases if self.cases else 0.0


def load_replay(directory: str | Path) -> tuple[ReplayCase, ...]:
    """Read every case directory, in name order."""
    base = Path(directory)
    folders = sorted(path for path in base.iterdir() if path.is_dir())
    return tuple(_load_case(folder) for folder in folders)


def run_replay(
    cases: Sequence[ReplayCase],
    repository: str | Path,
    *,
    budget: int = DEFAULT_BUDGET,
    isolate_network: bool = False,
) -> ReplayReport:
    """Replay every case: revert, check the tests fail, then search."""
    repo = Path(repository)
    outcomes: list[ReplayOutcome] = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="axiome-replay-") as temporary:
            root = Path(temporary)
            _materialise(repo, case, root)
            before = run_tests(root, case.tests, isolate_network=isolate_network)
            if before.passed:
                raise CodeError("code.replay_not_failing", id=case.id)
            result = generate(
                root,
                case.target,
                case.tests,
                budget=budget,
                depth=case.depth,
                extra_targets=case.extra_targets,
                isolate_network=isolate_network,
            )
        outcomes.append(ReplayOutcome(case, result.status, len(result.attempts)))
    return ReplayReport(tuple(outcomes))


def _load_case(folder: Path) -> ReplayCase:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"{folder}: expected a JSON object")
    files = {
        _relative(path, folder): path.read_text(encoding="utf-8")
        for path in sorted(folder.rglob("*"))
        if path.is_file() and not (path.parent == folder and path.name == "manifest.json")
    }
    return ReplayCase(
        str(manifest["id"]),
        str(manifest["commit"]),
        str(manifest["target"]),
        _strings(manifest["tests"]),
        _strings(manifest["changed"]),
        str(manifest["summary"]),
        int(str(manifest.get("depth", 1))),
        _strings(manifest.get("extra_targets", [])),
        files,
    )


def _relative(path: Path, folder: Path) -> str:
    return path.relative_to(folder).as_posix()


def _materialise(repo: Path, case: ReplayCase, root: Path) -> None:
    """Extract the tree of the fixing commit, then revert its source changes."""
    payload = _git(repo, "archive", case.commit)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        _extract(archive, root)
    base = root.resolve()
    for relative, text in case.files.items():
        destination = (root / relative).resolve()
        if not destination.is_relative_to(base):
            raise CodeError("code.outside_repository", path=relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")


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
        raise CodeError("code.replay_history", detail=str(exc)) from exc


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("expected a JSON array")
    return tuple(str(item) for item in value)
