from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from axiome.cli.main import execute, main
from axiome.kernel import Kernel


def test_execute_commands(kernel: Kernel) -> None:
    assert execute(kernel, "") == ""
    assert "Commands" in execute(kernel, ":help")
    assert "Unknown command" in execute(kernel, ":nope")
    assert "axiome:ontology" in execute(kernel, ":sources")
    assert "is_a_transitivity" in execute(kernel, ":rules")
    assert "No contradiction" in execute(kernel, ":conflicts")
    assert "PROVED" in execute(kernel, ":proof is_a(cat, animal)")
    assert execute(kernel, "is_a(felix, cat).").startswith("Noted")
    execute(kernel, "r(X) :- is_a(X, cat).")
    assert "% hypothesis" in execute(kernel, ":rules")
    assert "X = felix" in execute(kernel, "?- is_a(X, cat).")


def test_main_command_mode(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--memory", "-c", "?- is_a(cat, animal).", "-c", "p(X) :- q(Y)."])
    out = capsys.readouterr().out
    assert code == 1
    assert "Yes  [PROVED]" in out and "Error" in out


def test_main_lang_option(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--memory", "--lang", "fr", "-c", "?- is_a(cat, animal)."]) == 0
    assert "Oui  [PROUVÉ]" in capsys.readouterr().out


def test_main_db_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db = str(tmp_path / "x.db")
    assert main(["--db", db, "-c", "is_a(felix, cat)."]) == 0
    assert main(["--db", db, "-c", "?- is_a(felix, animal)."]) == 0
    assert "Yes" in capsys.readouterr().out


def test_repl(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    feed = iter(["?- is_a(cat, animal).", "p(", ":quit"])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(feed))
    assert main(["--memory"]) == 0
    out = capsys.readouterr().out
    assert "PROVED" in out and "Error" in out


def test_repl_eof(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setenv("AXIOME_DB", str(tmp_path / "e.db"))
    monkeypatch.setattr(builtins, "input", raise_eof)
    assert main([]) == 0
