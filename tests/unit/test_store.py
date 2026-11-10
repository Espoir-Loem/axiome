from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from axiome.core.clock import FixedClock, SystemClock
from axiome.core.config import Config
from axiome.core.errors import KnowledgeError, StorageError
from axiome.knowledge.seed import load_seed, seed_digest
from axiome.knowledge.store import KnowledgeStore
from axiome.reasoning.syntax import parse_atom
from axiome.reasoning.terms import Atom, Var
from axiome.verification.epistemic import Reliability, Source, SourceKind, Stance

SRC = Source("s", "Source", SourceKind.REFERENCE, Reliability.HIGH, "org", "https://x")


def test_evidence_round_trip_and_idempotence() -> None:
    st = KnowledgeStore()
    st.add_source(SRC)
    atom = parse_atom('p(a, "b c", 3)')
    assert st.add_evidence(atom, "s", Stance.SUPPORTS, "t0")
    assert not st.add_evidence(atom, "s", Stance.SUPPORTS, "t1")
    ev = st.evidence()
    assert list(ev) == [atom]
    assert ev[atom][0].source == SRC
    assert st.sources() == [SRC]


def test_errors() -> None:
    st = KnowledgeStore()
    with pytest.raises(KnowledgeError):
        st.add_evidence(parse_atom("p(a)"), "unknown", Stance.SUPPORTS, "t")
    st.add_source(SRC)
    with pytest.raises(KnowledgeError):
        st.add_evidence(Atom("p", (Var("X"),)), "s", Stance.SUPPORTS, "t")
    st.close()
    with pytest.raises(StorageError):
        st.set_meta("k", "v")


def test_rules_and_meta(tmp_path: Path) -> None:
    path = str(tmp_path / "sub" / "k.db")
    st = KnowledgeStore(path)
    assert st.add_rule("p(X) :- q(X).", axiomatic=False)
    assert not st.add_rule("p(X) :- q(X).", axiomatic=False)
    st.replace_axiomatic_rules("r(X) :- q(X).")
    st.replace_axiomatic_rules("s(X) :- q(X).")
    assert [r.text for r in st.rules()] == ["s(X) :- q(X).", "p(X) :- q(X)."]
    st.set_meta("k", "v")
    assert st.get_meta("k") == "v" and st.get_meta("missing") is None
    st.close()
    assert KnowledgeStore(path).get_meta("k") == "v"  # persistence


def test_schema_version_guard(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    con = sqlite3.connect(path)
    con.execute("PRAGMA user_version = 99")
    con.close()
    with pytest.raises(StorageError):
        KnowledgeStore(str(path))


def test_seed_is_idempotent() -> None:
    st = KnowledgeStore()
    assert load_seed(st, FixedClock())
    n = len(st.evidence())
    assert not load_seed(st, FixedClock())
    assert len(st.evidence()) == n > 50
    assert st.get_meta("seed_sha256") == seed_digest()


def test_config_and_clock() -> None:
    assert Config.from_env({"AXIOME_DB": "/x.db"}).db_path == "/x.db"
    assert Config.from_env({"XDG_DATA_HOME": "/d"}).db_path.endswith("axiome.db")
    assert Config.from_env().db_path
    assert "T" in SystemClock().now()
    assert FixedClock("t").now() == "t"
