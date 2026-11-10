from __future__ import annotations

import pytest

from axiome.verification.epistemic import (
    Evidence,
    Reliability,
    Source,
    SourceKind,
    Stance,
    Status,
    assess,
)

H, M, L = Reliability.HIGH, Reliability.MEDIUM, Reliability.LOW
P, C = Stance.SUPPORTS, Stance.CONTRADICTS


def src(
    sid: str, kind: SourceKind = SourceKind.REFERENCE, rel: Reliability = H, org: str | None = None
) -> Source:
    return Source(sid, sid.upper(), kind, rel, org or sid)


def ev(source: Source, stance: Stance = P) -> Evidence:
    return Evidence(source, stance)


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ([], Status.UNVERIFIED),
        ([ev(src("a", SourceKind.AXIOM))], Status.PROVED),
        ([ev(src("p", SourceKind.PROOF))], Status.PROVED),
        ([ev(src("c", SourceKind.COMPUTATION))], Status.VERIFIED),
        ([ev(src("a", SourceKind.AXIOM)), ev(src("c", SourceKind.COMPUTATION), C)], Status.REFUTED),
        ([ev(src("w")), ev(src("x"))], Status.CONFIRMED),
        ([ev(src("w")), ev(src("w2", org="w"))], Status.PLAUSIBLE),  # même organisation
        ([ev(src("w"))], Status.PLAUSIBLE),
        ([ev(src("m1", rel=M)), ev(src("m2", rel=M))], Status.PLAUSIBLE),
        ([ev(src("m1", rel=M))], Status.UNVERIFIED),
        ([ev(src("u", SourceKind.USER, L))], Status.UNVERIFIED),
        ([ev(src("w")), ev(src("x"), C)], Status.CONTESTED),
        ([ev(src("x"), C), ev(src("y"), C)], Status.REFUTED),
        ([ev(src("x"), C)], Status.UNVERIFIED),
        ([ev(src("u", rel=L)), ev(src("v", rel=L), C)], Status.CONTESTED),
        ([ev(src("v", rel=L), C)], Status.UNVERIFIED),
    ],
)
def test_rules(evidence: list[Evidence], expected: Status) -> None:
    result = assess(evidence)
    assert result.status is expected
    assert result.reasons


def test_assessment_independent_of_order() -> None:
    items = [ev(src("w")), ev(src("x")), ev(src("y"), C)]
    assert assess(items) == assess(list(reversed(items)))


def test_status_order_and_labels() -> None:
    assert Status.REFUTED < Status.CONTESTED < Status.PROVED
    assert Status.PLAUSIBLE <= Status.PLAUSIBLE
    assert min(Status.PROVED, Status.PLAUSIBLE) is Status.PLAUSIBLE
    assert Status.UNVERIFIED.label == "NON VÉRIFIÉ"
    assert Status.PROVED.__lt__(3) is NotImplemented
    assert Status.PROVED.__le__(3) is NotImplemented
