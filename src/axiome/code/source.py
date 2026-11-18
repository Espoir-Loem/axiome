"""Repository input for the code tools (M7): deterministic source files.

Reading is deliberately boring: only ``*.py`` files, sorted by POSIX path,
newlines normalised, caches and environments skipped. Two runs over the same
tree must yield the same tuple of files, byte for byte (RFC-0002).

Positions are written ``path:line`` so they can be used directly as Axiome
constants in facts (see :mod:`axiome.code.facts`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from axiome.core.errors import CodeError

#: Directories never scanned, at any depth: caches, environments, build outputs.
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)
_SOURCE_SUFFIX = ".py"
#: Generated metadata directories (``pkg.egg-info``).
_GENERATED_SUFFIX = ".egg-info"


@dataclass(frozen=True, slots=True)
class Position:
    """A place in the repository, written ``path:line``."""

    path: str  # POSIX, relative to the repository root
    line: int  # 1-based

    def __str__(self) -> str:
        return f"{self.path}:{self.line}"

    @classmethod
    def parse(cls, text: str) -> Position:
        """Read back a ``path:line`` position. Raise ``ValueError`` if malformed."""
        path, separator, line = text.rpartition(":")
        if not separator or not path or not line.isdigit() or int(line) < 1:
            raise ValueError(f"bad position {text!r}; expected path:line")
        return cls(path, int(line))


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One Python file: its repository-relative POSIX path and its text."""

    path: str
    text: str


def normalize_newlines(text: str) -> str:
    """Use ``\\n`` only, whatever the checkout's line endings."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def module_name(path: str) -> str:
    """Dotted module name of a source path.

    The conventional ``src/`` layout is unwrapped and ``__init__`` collapsed:
    ``src/axiome/core/config.py`` is ``axiome.core.config``.
    """
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if not parts or not parts[-1].endswith(_SOURCE_SUFFIX):
        raise ValueError(f"not a Python source path: {path!r}")
    if len(parts) > 1 and parts[0] == "src":
        parts = parts[1:]
    stem = parts[-1][: -len(_SOURCE_SUFFIX)]
    parts = [*parts[:-1], stem]
    if stem == "__init__" and len(parts) > 1:
        parts = parts[:-1]
    return ".".join(parts)


def read_repository(root: str | Path) -> tuple[SourceFile, ...]:
    """Read every Python source file under ``root``, sorted by path."""
    base = Path(root)
    if not base.is_dir():
        raise CodeError("code.not_a_directory", path=str(root))
    files: list[SourceFile] = []
    for path in base.rglob(f"*{_SOURCE_SUFFIX}"):
        relative = path.relative_to(base)
        if _ignored(relative):
            continue
        name = relative.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CodeError("code.unreadable_file", path=name, detail=exc) from exc
        files.append(SourceFile(name, normalize_newlines(text)))
    return tuple(sorted(files, key=lambda source: source.path))


def _ignored(relative: Path) -> bool:
    return any(
        part in IGNORED_DIRECTORIES or part.endswith(_GENERATED_SUFFIX)
        for part in relative.parts[:-1]
    )
