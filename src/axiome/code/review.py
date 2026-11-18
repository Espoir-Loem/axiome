"""Review a unified diff: new diagnostics only, each backed by facts (M7.1).

The repository on disk is never touched: the diff is applied in memory, both
trees are indexed, and only diagnostics that appear *after* the change are
kept. A rule already violated elsewhere is not blamed twice (RFC-0002).

The output is plain :class:`~axiome.code.analyze.Diagnostic` values; turning
them into reviewed sentences is the team's job (``axiome.team.code_review``),
so this package stays independent from the conversation layer.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from axiome.code.analyze import AnalysisConfig, Diagnostic, analyze, load_config
from axiome.code.index import CodeIndex
from axiome.code.source import Position, SourceFile, read_repository
from axiome.core.errors import CodeError

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True, slots=True)
class FilePatch:
    """One file section of a unified diff (``None`` on the absent side)."""

    old_path: str | None
    new_path: str | None
    hunks: tuple[tuple[int, int, tuple[tuple[str, str], ...]], ...]  # (old_start, old_count, lines)


def parse_diff(diff: str) -> tuple[FilePatch, ...]:
    """Parse a unified diff. Raise ``CodeError`` when it is malformed."""
    lines = diff.splitlines()
    patches: list[FilePatch] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("--- "):
            index += 1
            continue
        old_path = _diff_path(lines[index][4:])
        if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise CodeError("code.bad_diff", detail="missing +++ header")
        new_path = _diff_path(lines[index + 1][4:])
        index += 2
        hunks: list[tuple[int, int, tuple[tuple[str, str], ...]]] = []
        while index < len(lines) and lines[index].startswith("@@"):
            hunk, index = _parse_hunk(lines, index)
            hunks.append(hunk)
        if not hunks:
            raise CodeError("code.bad_diff", detail=f"no hunk for {old_path or new_path}")
        patches.append(FilePatch(old_path, new_path, tuple(hunks)))
    if not patches:
        raise CodeError("code.bad_diff", detail="no file header")
    return tuple(patches)


def _parse_hunk(
    lines: list[str], index: int
) -> tuple[tuple[int, int, tuple[tuple[str, str], ...]], int]:
    header = _HUNK.match(lines[index])
    if header is None:
        raise CodeError("code.bad_diff", detail=f"bad hunk header {lines[index]!r}")
    old_start, old_count = int(header.group(1)), int(header.group(2) or 1)
    index += 1
    body: list[tuple[str, str]] = []
    while index < len(lines):
        line = lines[index]
        if _starts_file(lines, index) or line.startswith("@@"):
            break
        if line.startswith("\\"):  # "\ No newline at end of file"
            index += 1
            continue
        if line[:1] not in (" ", "+", "-"):
            break
        body.append((line[:1], line[1:]))
        index += 1
    return (old_start, old_count, tuple(body)), index


def _starts_file(lines: list[str], index: int) -> bool:
    """True if ``index`` is a ``---`` header followed by a ``+++`` header."""
    return (
        lines[index].startswith("--- ")
        and index + 1 < len(lines)
        and lines[index + 1].startswith("+++ ")
    )


def _diff_path(header: str) -> str | None:
    name = header.split("\t", 1)[0].strip()
    if name == "/dev/null":
        return None
    for prefix in ("a/", "b/"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def apply_diff(files: Mapping[str, str], diff: str) -> dict[str, str]:
    """Apply a unified diff to an in-memory tree; return a new tree."""
    out = dict(files)
    for patch in parse_diff(diff):
        old_lines = [] if patch.old_path is None else _lines_of(out, patch.old_path)
        result = _apply_patch(old_lines, patch.hunks)
        if patch.old_path is not None and patch.old_path != patch.new_path:
            out.pop(patch.old_path, None)
        if patch.new_path is not None:
            out[patch.new_path] = "\n".join(result)
    return out


def _apply_patch(
    old_lines: list[str], hunks: tuple[tuple[int, int, tuple[tuple[str, str], ...]], ...]
) -> list[str]:
    result: list[str] = []
    cursor = 0
    for old_start, old_count, body in hunks:
        start = old_start if old_count == 0 else old_start - 1
        if start < cursor or start > len(old_lines):
            raise CodeError("code.bad_diff", detail="hunk out of range")
        result.extend(old_lines[cursor:start])
        cursor = _apply_body(result, start, body)
    result.extend(old_lines[cursor:])
    return result


def _apply_body(result: list[str], start: int, body: tuple[tuple[str, str], ...]) -> int:
    cursor = start
    for kind, text in body:
        if kind == " ":
            result.append(text)
            cursor += 1
        elif kind == "-":
            cursor += 1
        else:
            result.append(text)
    return cursor


def _lines_of(files: Mapping[str, str], path: str) -> list[str]:
    if path not in files:
        raise CodeError("code.diff_unknown_path", path=path)
    return files[path].splitlines()


def review_diff(
    root: str | Path, diff: str, config: AnalysisConfig | None = None
) -> tuple[Diagnostic, ...]:
    """Diagnostics introduced by ``diff`` on the tree at ``root``."""
    settings = config or load_config(Path(root) / "pyproject.toml")
    before = read_repository(root)
    after_map = apply_diff({source.path: source.text for source in before}, diff)
    after = tuple(SourceFile(path, text) for path, text in sorted(after_map.items()))
    previous = _keyed(analyze(CodeIndex.build(before), settings))
    current = analyze(CodeIndex.build(after), settings)
    remaining = previous.copy()
    fresh: list[Diagnostic] = []
    for diagnostic in current:
        key = _key(diagnostic)
        if remaining[key]:
            remaining[key] -= 1
            continue
        fresh.append(diagnostic)
    return tuple(fresh)


def _keyed(diagnostics: tuple[Diagnostic, ...]) -> Counter[tuple[str, str, str]]:
    return Counter(_key(diagnostic) for diagnostic in diagnostics)


def _key(diagnostic: Diagnostic) -> tuple[str, str, str]:
    return (diagnostic.rule, Position.parse(diagnostic.position).path, diagnostic.line.strip())
