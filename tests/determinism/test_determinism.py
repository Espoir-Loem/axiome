"""Garantie centrale : même entrée → même sortie, octet pour octet, entre processus.

Chaque processus Python a une graine de hachage différente (PYTHONHASHSEED) ;
si un ordre dépendait d'un set/dict non trié, les sorties divergeraient.
"""

from __future__ import annotations

import os
import subprocess
import sys

SCRIPT = [
    "?- est_un(X, animal).",
    ":preuve est_un(chat, animal)",
    "est_un(chat, oiseau).",
    "est_un(x, mammifère).",
    "est_un(x, oiseau).",
    ":conflits",
    "?- est_un(X, algorithme_de_tri), non a_propriete(X, stable).",
    "?- est_un(X, patron_de_conception), a_propriete(X, P).",
    "?- a_propriete(X, Y).",
]


def run(hash_seed: str) -> bytes:
    args = [sys.executable, "-m", "axiome", "--memoire"]
    for line in SCRIPT:
        args += ["-c", line]
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    return subprocess.run(args, capture_output=True, check=True, env=env).stdout


def test_output_identical_across_processes_and_hash_seeds() -> None:
    outputs = {run(seed) for seed in ("0", "1", "12345", "random")}
    assert len(outputs) == 1
    assert b"PROUV" in outputs.pop()
