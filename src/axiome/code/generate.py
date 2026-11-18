"""Bounded, execution-verified repair search (M7.3).

No pre-trained model: candidates are small, deterministic mutations of the
target file (literals, boolean constants, comparison operators, ``not``).
Each candidate runs the project's tests in the sandbox, on a temporary copy.
A patch is accepted only when the tests really pass; otherwise the search
reports the rejected candidates and their outcome. Nothing is ever presented
as correct on the strength of its shape (RFC-0002).
"""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

from axiome.code.sandbox import SandboxLimits, run_tests
from axiome.core.errors import CodeError

DEFAULT_BUDGET = 50
ACCEPTED = "accepted"
BUDGET_EXHAUSTED = "budget_exhausted"
NO_CANDIDATES = "no_candidates"


@dataclass(frozen=True, slots=True)
class Attempt:
    """One candidate and the verdict of its execution."""

    index: int
    patch: str
    passed: bool
    report: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """The outcome of one bounded search."""

    status: str
    patch: str = ""
    attempts: tuple[Attempt, ...] = ()
    seed: int = 0
    budget: int = DEFAULT_BUDGET

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTED


@dataclass(frozen=True, slots=True)
class _Edit:
    """A replacement of ``text[lineno][start:end]``."""

    lineno: int
    start: int
    end: int
    replacement: str


@dataclass(frozen=True, slots=True)
class _Candidate:
    index: int
    patch: str
    text: str


def generate(
    root: str | Path,
    target: str,
    tests: tuple[str, ...] = (),
    *,
    budget: int = DEFAULT_BUDGET,
    seed: int = 0,
    limits: SandboxLimits | None = None,
    isolate_network: bool = True,
) -> GenerationResult:
    """Search at most ``budget`` deterministic candidates and keep the first that passes."""
    if budget < 1:
        raise CodeError("code.bad_budget", value=budget)
    base = Path(root)
    source = base / target
    if not source.is_file():
        raise CodeError("code.unknown_file", path=target)
    original = source.read_text(encoding="utf-8")
    candidates = _candidates(target, original, budget, seed)
    if not candidates:
        return GenerationResult(NO_CANDIDATES, seed=seed, budget=budget)
    attempts: list[Attempt] = []
    for candidate in candidates:
        result = run_tests(
            base,
            tests,
            limits,
            isolate_network=isolate_network,
            overlay={target: candidate.text},
        )
        attempt = Attempt(candidate.index, candidate.patch, result.passed, result.report())
        attempts.append(attempt)
        if result.passed:
            return GenerationResult(ACCEPTED, candidate.patch, tuple(attempts), seed, budget)
    return GenerationResult(BUDGET_EXHAUSTED, "", tuple(attempts), seed, budget)


def _candidates(target: str, text: str, budget: int, seed: int) -> tuple[_Candidate, ...]:
    """Build the canonical candidate list, rotated deterministically by ``seed``."""
    lines = text.splitlines()
    newline = "\n" if text.endswith("\n") else ""
    try:
        tree = ast.parse(text, filename=target)
    except SyntaxError as exc:
        raise CodeError(
            "code.syntax_error", path=target, line=exc.lineno or 0, detail=exc.msg
        ) from exc
    edits: list[_Edit] = []
    for node in ast.walk(tree):
        edits.extend(_node_edits(lines, node))
    edits.sort(key=lambda edit: (edit.lineno, edit.start, edit.end, edit.replacement))
    seen = {text}
    candidates: list[_Candidate] = []
    for edit in edits:
        changed = _apply(lines, edit, newline)
        if changed in seen:
            continue
        seen.add(changed)
        patch = _unified(target, text, changed)
        if patch:
            candidates.append(_Candidate(len(candidates), patch, changed))
    if not candidates:
        return ()
    offset = seed % len(candidates)
    ordered = [*candidates[offset:], *candidates[:offset]]
    return tuple(ordered[:budget])


def _node_edits(lines: list[str], node: ast.AST) -> list[_Edit]:
    """The mutations available on one node, in a fixed order."""
    if isinstance(node, ast.Constant):
        return _constant_edits(lines, node)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _not_edit(lines, node)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and _single_line(node):
        return _comparison_edit(lines, node)
    return []


def _constant_edits(lines: list[str], node: ast.Constant) -> list[_Edit]:
    if not _single_line(node) or node.end_col_offset is None:
        return []
    line = lines[node.lineno - 1]
    segment = line[node.col_offset : node.end_col_offset]
    return [
        _Edit(node.lineno, node.col_offset, node.end_col_offset, str(value))
        for value in _constant_values(node.value)
        if str(value) != segment
    ]


def _not_edit(lines: list[str], node: ast.UnaryOp) -> list[_Edit]:
    operand = node.operand
    if node.lineno != operand.lineno:
        return []
    line = lines[node.lineno - 1]
    segment = line[node.col_offset : operand.col_offset]
    if segment.strip() != "not":
        return []
    start = node.col_offset + segment.index("not")
    end = start + 3
    if line[end : end + 1] == " ":
        end += 1
    return [_Edit(node.lineno, start, end, "")]


def _comparison_edit(lines: list[str], node: ast.Compare) -> list[_Edit]:
    left, right = node.left, node.comparators[0]
    if left.end_lineno != right.lineno or left.end_col_offset is None:
        return []
    line = lines[node.lineno - 1]
    segment = line[left.end_col_offset : right.col_offset]
    old = _COMPARISONS.get(type(node.ops[0]))
    if old is None:
        return []
    for symbol in old:
        if symbol in segment:
            start = left.end_col_offset + segment.index(symbol)
            return [_Edit(node.lineno, start, start + len(symbol), _OPPOSITE[symbol])]
    return []


def _single_line(node: ast.expr) -> bool:
    return node.end_lineno == node.lineno


def _constant_values(value: object) -> tuple[object, ...]:
    if isinstance(value, bool):
        return (not value,)
    if isinstance(value, int) and not isinstance(value, bool):
        return tuple(n for n in (0, 1, -1, value - 1, value + 1, value * 2) if n != value)
    return ()


def _apply(lines: list[str], edit: _Edit, newline: str) -> str:
    line = lines[edit.lineno - 1]
    changed = f"{line[: edit.start]}{edit.replacement}{line[edit.end :]}"
    out = [*lines[: edit.lineno - 1], changed, *lines[edit.lineno :]]
    return "\n".join(out) + newline


def _unified(target: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{target}",
            tofile=f"b/{target}",
        )
    )


_COMPARISONS: dict[type[ast.cmpop], tuple[str, ...]] = {
    ast.Eq: ("==",),
    ast.NotEq: ("!=",),
    ast.Lt: ("<",),
    ast.Gt: (">",),
    ast.LtE: ("<=",),
    ast.GtE: (">=",),
    ast.In: ("not in", "in"),
    ast.NotIn: ("not in", "in"),
    ast.Is: ("is not", "is"),
    ast.IsNot: ("is not", "is"),
}
_OPPOSITE = {
    "==": "!=",
    "!=": "==",
    "<": ">=",
    ">=": "<",
    ">": "<=",
    "<=": ">",
    "in": "not in",
    "not in": "in",
    "is": "is not",
    "is not": "is",
}
