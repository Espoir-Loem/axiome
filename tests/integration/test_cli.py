from __future__ import annotations

import builtins
from collections.abc import Iterator

import pytest

from axiome.cli.main import execute, main
from axiome.kernel import Kernel


def test_execute_commands(kernel: Kernel) -> None:
    assert execute(kernel, "") == ""
    assert "Commandes" in execute(kernel, ":aide")
    assert "inconnue" in execute(kernel, ":nimporte")
    assert "axiome:ontologie" in execute(kernel, ":sources")
    assert "transitivite_est_un" in execute(kernel, ":regles")
    assert "Aucune contradiction" in execute(kernel, ":conflits")
    assert "PROUVÉ" in execute(kernel, ":preuve est_un(chat, animal)")
    assert execute(kernel, "est_un(félix, chat).").startswith("Noté")
    execute(kernel, "r(X) :- est_un(X, chat).")
    assert "% hypothèse" in execute(kernel, ":regles")
    assert "X = félix" in execute(kernel, "?- est_un(X, chat).")


def test_main_command_mode(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--memoire", "-c", "?- est_un(chat, animal).", "-c", "p(X) :- q(Y)."])
    out = capsys.readouterr().out
    assert code == 1
    assert "Oui  [PROUVÉ]" in out and "Erreur" in out


def test_main_db_option(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:  # type: ignore[no-untyped-def]
    db = str(tmp_path / "x.db")
    assert main(["--db", db, "-c", "est_un(félix, chat)."]) == 0
    assert main(["--db", db, "-c", "?- est_un(félix, animal)."]) == 0
    assert "Oui" in capsys.readouterr().out


def _feed(lines: list[str]) -> Iterator[str]:
    yield from lines


def test_repl(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    feed = _feed(["?- est_un(chat, animal).", "p(", ":quitter"])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(feed))
    assert main(["--memoire"]) == 0
    out = capsys.readouterr().out
    assert "PROUVÉ" in out and "Erreur" in out


def test_repl_eof(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    def raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setenv("AXIOME_DB", str(tmp_path / "e.db"))
    monkeypatch.setattr(builtins, "input", raise_eof)
    assert main([]) == 0
