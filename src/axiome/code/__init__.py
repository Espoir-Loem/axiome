"""Code tools (M7): analysis, review and execution-verified generation."""

from axiome.code.analyze import (
    RULES,
    AnalysisConfig,
    Diagnostic,
    analyze,
    load_config,
)
from axiome.code.facts import PREDICATES, extract
from axiome.code.generate import (
    ACCEPTED,
    BUDGET_EXHAUSTED,
    NO_CANDIDATES,
    Attempt,
    GenerationResult,
    generate,
)
from axiome.code.index import CodeIndex, Problem
from axiome.code.review import apply_diff, parse_diff, review_diff
from axiome.code.sandbox import SandboxLimits, SandboxResult, run, run_tests
from axiome.code.source import Position, SourceFile, module_name, read_repository

__all__ = [
    "ACCEPTED",
    "BUDGET_EXHAUSTED",
    "NO_CANDIDATES",
    "PREDICATES",
    "RULES",
    "AnalysisConfig",
    "Attempt",
    "CodeIndex",
    "Diagnostic",
    "GenerationResult",
    "Position",
    "Problem",
    "SandboxLimits",
    "SandboxResult",
    "SourceFile",
    "analyze",
    "apply_diff",
    "extract",
    "generate",
    "load_config",
    "module_name",
    "parse_diff",
    "read_repository",
    "review_diff",
    "run",
    "run_tests",
]
