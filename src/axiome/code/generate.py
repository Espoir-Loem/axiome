"""Bounded, execution-verified repair search (M7.3, widened in M7.7).

No pre-trained model: candidates are small, deterministic mutations of the
target files (literals, boolean constants, comparison and binary operators,
boolean operators, ``not``, and negated conditions). Each candidate runs the
project's tests in the sandbox, on a temporary copy.

``depth`` composes up to that many edits on distinct lines, and ``extra_targets``
lets a composition span several files; the search is breadth-first and every
attempt is a complete patch evaluated by the tests. A patch is accepted only
when the tests really pass; otherwise the search reports the rejected candidates
and their outcome. Nothing is ever presented as correct on the strength of its
shape (RFC-0002).
"""

from __future__ import annotations

import ast
import difflib
import re
from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from axiome.code.sandbox import SandboxLimits, run_tests
from axiome.core.errors import CodeError, CodeSyntaxError

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
    lineno: int
    text: str


@dataclass(frozen=True, slots=True)
class _State:
    """A partial patch: file contents, touched lines and its depth."""

    files: Mapping[str, str]
    edited: frozenset[tuple[str, int]]
    depth: int


def generate(
    root: str | Path,
    target: str,
    tests: tuple[str, ...] = (),
    *,
    budget: int = DEFAULT_BUDGET,
    seed: int = 0,
    limits: SandboxLimits | None = None,
    isolate_network: bool = True,
    extra_targets: tuple[str, ...] = (),
    depth: int = 1,
    diagnostics: str = "",
) -> GenerationResult:
    """Search at most ``budget`` deterministic patches and keep the first that passes.

    A patch is one edit, or a composition of at most ``depth`` edits on distinct
    lines, possibly spread over ``extra_targets``. States are visited breadth-first:
    every single edit is tried before a composition of two, and so on. The budget
    counts executed attempts at every depth, and the tests alone decide acceptance.

    ``diagnostics`` is the failing test output. Its identifiers only reorder the
    candidates: a line naming the failing test's subject is tried first. It never
    supplies patch text and never changes which mutations exist.
    """
    if budget < 1:
        raise CodeError("code.bad_budget", value=budget)
    if depth < 1:
        raise CodeError("code.bad_depth", value=depth)
    base = Path(root)
    paths = (target, *(path for path in extra_targets if path != target))
    originals: dict[str, str] = {}
    for path in paths:
        source = base / path
        if not source.is_file():
            raise CodeError("code.unknown_file", path=path)
        originals[path] = source.read_text(encoding="utf-8")
    attempts: list[Attempt] = []
    terms = _diagnostic_terms(diagnostics)
    states = deque([_State(originals, frozenset(), 0)])
    seen = {_key(originals)}
    while states:
        state = states.popleft()
        for child in _children(state, paths, seed, seen, terms):
            if len(attempts) >= budget:
                return GenerationResult(BUDGET_EXHAUSTED, "", tuple(attempts), seed, budget)
            patch = _combined_patch(originals, child.files)
            outcome = run_tests(
                base,
                tests,
                limits,
                isolate_network=isolate_network,
                overlay=dict(child.files),
            )
            attempts.append(Attempt(len(attempts), patch, outcome.passed, outcome.report()))
            if outcome.passed:
                return GenerationResult(ACCEPTED, patch, tuple(attempts), seed, budget)
            if child.depth < depth:
                states.append(child)
    if not attempts:
        return GenerationResult(NO_CANDIDATES, seed=seed, budget=budget)
    return GenerationResult(BUDGET_EXHAUSTED, "", tuple(attempts), seed, budget)


def _key(files: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(files.items()))


def _children(
    state: _State,
    paths: tuple[str, ...],
    seed: int,
    seen: set[tuple[tuple[str, str], ...]],
    terms: frozenset[str] = frozenset(),
) -> Iterator[_State]:
    """Yield unseen states with one more edit, in a fixed order."""
    for path in paths:
        skip = frozenset(lineno for edited, lineno in state.edited if edited == path)
        for candidate in _candidates(path, state.files[path], seed, skip, terms):
            files = {**state.files, path: candidate.text}
            key = _key(files)
            if key in seen:
                continue
            seen.add(key)
            yield _State(files, state.edited | {(path, candidate.lineno)}, state.depth + 1)


def _candidates(
    target: str,
    text: str,
    seed: int,
    skip: frozenset[int] = frozenset(),
    terms: frozenset[str] = frozenset(),
) -> tuple[_Candidate, ...]:
    """Build the canonical candidate list, rotated deterministically by ``seed``."""
    lines = text.splitlines()
    newline = "\n" if text.endswith("\n") else ""
    try:
        tree = ast.parse(text, filename=target)
    except SyntaxError as exc:
        raise CodeSyntaxError(
            "code.syntax_error", path=target, line=exc.lineno or 0, detail=exc.msg
        ) from exc
    edits: list[_Edit] = []
    for node in ast.walk(tree):
        edits.extend(_node_edits(lines, node))
    edits.sort(key=lambda edit: (edit.lineno, edit.start, edit.end, edit.replacement))
    edits = [edit for edit in edits if edit.lineno not in skip]
    seen = {text}
    candidates: list[_Candidate] = []
    for edit in edits:
        changed = _apply(lines, edit, newline)
        if changed in seen:
            continue
        seen.add(changed)
        if _unified(target, text, changed):
            candidates.append(_Candidate(edit.lineno, changed))
    if not candidates:
        return ()
    if terms:
        source = [line.casefold() for line in lines]
        ranked = sorted(
            enumerate(candidates),
            key=lambda pair: (
                -sum(
                    term in " ".join(source[max(0, pair[1].lineno - 3) : pair[1].lineno])
                    for term in terms
                ),
                pair[0],
            ),
        )
        candidates = [candidate for _, candidate in ranked]
    offset = seed % len(candidates)
    return (*candidates[offset:], *candidates[:offset])


def _diagnostic_terms(text: str) -> frozenset[str]:
    """Names from a failing test run, used only to order the candidates."""
    terms: set[str] = set()
    for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        name = word.casefold()
        if len(name) >= 3 and name not in _DIAGNOSTIC_STOP:
            terms.add(name)
        for part in name.split("_"):
            if len(part) >= 3 and part not in _DIAGNOSTIC_STOP:
                terms.add(part)
    return frozenset(terms)


def _node_edits(lines: list[str], node: ast.AST) -> list[_Edit]:
    """The mutations available on one node, in a fixed order."""
    if isinstance(node, ast.Constant):
        return _constant_edits(lines, node)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _not_edit(lines, node)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and _single_line(node):
        return _comparison_edit(lines, node)
    if isinstance(node, ast.BinOp):
        return _binary_edit(lines, node)
    if isinstance(node, ast.BoolOp):
        return _boolean_edit(lines, node)
    if isinstance(node, (ast.If, ast.IfExp)):
        return _condition_edit(lines, node.test)
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


def _binary_edit(lines: list[str], node: ast.BinOp) -> list[_Edit]:
    left, right = node.left, node.right
    if left.end_lineno != right.lineno or left.end_col_offset is None:
        return []
    line = lines[node.lineno - 1]
    segment = line[left.end_col_offset : right.col_offset]
    symbol = segment.strip()
    replacements = _OPPOSITE_OPERATORS.get(symbol)
    if replacements is None:
        return []
    start = left.end_col_offset + segment.index(symbol)
    return [
        _Edit(node.lineno, start, start + len(symbol), replacement) for replacement in replacements
    ]


def _boolean_edit(lines: list[str], node: ast.BoolOp) -> list[_Edit]:
    first, second = node.values[0], node.values[1]
    if first.end_lineno != second.lineno or first.end_col_offset is None:
        return []
    line = lines[node.lineno - 1]
    segment = line[first.end_col_offset : second.col_offset]
    symbol = segment.strip()
    replacement = _OPPOSITE_BOOLEANS.get(symbol)
    if replacement is None:
        return []
    start = first.end_col_offset + segment.index(symbol)
    return [_Edit(node.lineno, start, start + len(symbol), replacement)]


def _condition_edit(lines: list[str], test: ast.expr) -> list[_Edit]:
    """Insert ``not`` before a condition, unless it is already negated."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return []
    line = lines[test.lineno - 1]
    before = line[: test.col_offset]
    if not before.rstrip().endswith(("if", "elif", "while")):
        return []
    return [_Edit(test.lineno, test.col_offset, test.col_offset, "not ")]


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


def _combined_patch(originals: Mapping[str, str], files: Mapping[str, str]) -> str:
    return "\n".join(
        _unified(path, originals[path], files[path]).rstrip("\n")
        for path in originals
        if files[path] != originals[path]
    )


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
_OPPOSITE_OPERATORS: dict[str, tuple[str, ...]] = {
    "+": ("-",),
    "-": ("+",),
    "*": ("//",),
    "/": ("//",),
    "//": ("*",),
    "%": ("//",),
}
_OPPOSITE_BOOLEANS = {"and": "or", "or": "and"}
_DIAGNOSTIC_STOP = frozenset(
    {
        "actual",
        "assert",
        "assertion",
        "assertionerror",
        "cannot",
        "error",
        "expected",
        "failed",
        "failure",
        "false",
        "from",
        "import",
        "importerror",
        "info",
        "line",
        "lines",
        "module",
        "name",
        "none",
        "passed",
        "patch",
        "result",
        "return",
        "self",
        "short",
        "summary",
        "test",
        "tests",
        "true",
        "value",
        "where",
    }
)
