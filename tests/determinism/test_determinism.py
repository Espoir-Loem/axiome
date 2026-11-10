"""Core guarantee: same input, same output, byte for byte, across processes.

Each Python process gets a different hash seed (PYTHONHASHSEED); if any order
depended on an unsorted set or dict, the outputs would diverge.
"""

from __future__ import annotations

import os
import subprocess
import sys

SCRIPT = [
    "?- is_a(X, animal).",
    ":proof is_a(cat, animal)",
    "is_a(cat, bird).",
    "is_a(x, mammal).",
    "is_a(x, bird).",
    ":conflicts",
    "?- is_a(X, sorting_algorithm), not has_property(X, stable).",
    "?- is_a(X, design_pattern), has_property(X, P).",
    "?- has_property(X, Y).",
]


def run(hash_seed: str) -> bytes:
    args = [sys.executable, "-m", "axiome", "--memory", "--lang", "en"]
    for line in SCRIPT:
        args += ["-c", line]
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    return subprocess.run(args, capture_output=True, check=True, env=env).stdout


def test_output_identical_across_processes_and_hash_seeds() -> None:
    outputs = {run(seed) for seed in ("0", "1", "12345", "random")}
    assert len(outputs) == 1
    assert b"PROVED" in outputs.pop()
