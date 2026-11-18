"""Repository reading: deterministic, sorted, and honest about failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from axiome.code.source import (
    Position,
    SourceFile,
    module_name,
    normalize_newlines,
    read_repository,
)
from axiome.core.errors import CodeError


def test_position_round_trip() -> None:
    for path, line in (("a.py", 1), ("pkg/é t.py", 42), ("a:b.py", 7), ("a:", 3)):
        position = Position(path, line)
        assert str(position) == f"{path}:{line}"
        assert Position.parse(str(position)) == position


@pytest.mark.parametrize("text", ["", "a.py", "a.py:", "a.py:0", "a.py:x", ":3", "a.py:-1"])
def test_bad_position(text: str) -> None:
    with pytest.raises(ValueError, match="expected path:line"):
        Position.parse(text)


def test_module_name() -> None:
    assert module_name("src/axiome/core/config.py") == "axiome.core.config"
    assert module_name("src/axiome/__init__.py") == "axiome"
    assert module_name("pkg/__init__.py") == "pkg"
    assert module_name("m.py") == "m"
    with pytest.raises(ValueError, match="not a Python source path"):
        module_name("notes.txt")


def test_normalize_newlines() -> None:
    assert normalize_newlines("a\r\nb\rc\n") == "a\nb\nc\n"


def test_read_repository_is_sorted_and_filtered(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "pkg" / "b.py").write_text("x = 1\r\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("y = 2\r", encoding="utf-8")
    for ignored in (".venv", "__pycache__", "pkg.egg-info", "build"):
        (tmp_path / ignored).mkdir()
        (tmp_path / ignored / "noise.py").write_text("z = 3\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("nope", encoding="utf-8")

    files = read_repository(tmp_path)

    assert [file.path for file in files] == ["a.py", "src/pkg/__init__.py", "src/pkg/b.py"]
    assert all(isinstance(file, SourceFile) for file in files)
    assert files[0].text == "y = 2\n"
    assert files[2].text == "x = 1\n"


def test_read_repository_errors(tmp_path: Path) -> None:
    with pytest.raises(CodeError):
        read_repository(tmp_path / "missing")
    (tmp_path / "bad.py").write_bytes(b"\xff\xfe")
    with pytest.raises(CodeError) as error:
        read_repository(tmp_path)
    assert "bad.py" in str(error.value)
