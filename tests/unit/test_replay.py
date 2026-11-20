"""Replay bench: manifests describe how far the bounded search may go."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from axiome.evaluation import replay
from axiome.evaluation.replay import ReplayCase, load_replay, run_replay

MANIFEST = {
    "id": "default",
    "commit": "abc",
    "target": "mod.py",
    "tests": ["test_mod.py"],
    "changed": ["mod.py", "helper.py"],
    "summary": "example",
}


def _case(directory: Path, manifest: dict[str, object], *files: str) -> None:
    directory.mkdir()
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in files:
        (directory / name).write_text("def f():\n    return 1\n", encoding="utf-8")


def test_load_replay_reads_defaults_and_composition(tmp_path: Path) -> None:
    _case(tmp_path / "a-default", MANIFEST, "mod.py", "helper.py")
    explicit = {**MANIFEST, "id": "composed", "depth": 2, "extra_targets": ["helper.py"]}
    _case(tmp_path / "b-composed", explicit, "mod.py", "helper.py")

    cases = load_replay(tmp_path)
    assert [case.id for case in cases] == ["default", "composed"]
    assert cases[0].depth == 1
    assert cases[0].extra_targets == ()
    assert cases[1].depth == 2
    assert cases[1].extra_targets == ("helper.py",)
    assert cases[0].files.keys() == {"mod.py", "helper.py"}


def test_run_replay_forwards_composition_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_generate(root: Path, target: str, tests: tuple[str, ...], **kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(status="budget_exhausted", attempts=())

    monkeypatch.setattr(replay, "generate", fake_generate)
    monkeypatch.setattr(replay, "run_tests", lambda *a, **k: SimpleNamespace(passed=False))
    monkeypatch.setattr(replay, "_materialise", lambda *a, **k: None)

    case = ReplayCase(
        "id",
        "commit",
        "mod.py",
        ("test_mod.py",),
        ("mod.py",),
        "summary",
        2,
        ("helper.py",),
    )
    report = run_replay([case], tmp_path, budget=7, isolate_network=False)

    assert captured["budget"] == 7
    assert captured["depth"] == 2
    assert captured["extra_targets"] == ("helper.py",)
    assert captured["isolate_network"] is False
    assert report.cases == 1
    assert report.accepted == 0
