"""Idempotent loading of the initial knowledge (``axiome/data/seed``).

The seed is versioned by its SHA-256 digest: if the content changes it is
reloaded; if it is unchanged nothing is rewritten.
"""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from typing import Any

from axiome.core.clock import Clock
from axiome.knowledge.store import KnowledgeStore
from axiome.reasoning.syntax import parse_atom
from axiome.verification.epistemic import Reliability, Source, SourceKind, Stance

SEED_PACKAGE = "axiome.data.seed"
RULES_FILE = "rules.axl"
FACTS_FILE = "facts.json"


def _read(name: str) -> str:
    return resources.files(SEED_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def seed_digest() -> str:
    h = hashlib.sha256()
    for name in (RULES_FILE, FACTS_FILE):
        h.update(name.encode())
        h.update(_read(name).encode())
    return h.hexdigest()


def load_seed(store: KnowledgeStore, clock: Clock) -> bool:
    """Load the seed if needed. Return True if anything was loaded."""
    digest = seed_digest()
    if store.get_meta("seed_sha256") == digest:
        return False
    store.replace_axiomatic_rules(_read(RULES_FILE))
    data: dict[str, Any] = json.loads(_read(FACTS_FILE))
    for s in data["sources"]:
        store.add_source(
            Source(
                id=s["id"],
                name=s["name"],
                kind=SourceKind(s["kind"]),
                reliability=Reliability[s["reliability"]],
                organization=s["organization"],
                url=s.get("url", ""),
            )
        )
    now = clock.now()
    for group in data["facts"]:
        for text in group["facts"]:
            store.add_evidence(parse_atom(text), group["source"], Stance.SUPPORTS, now)
    store.set_meta("seed_sha256", digest)
    return True
