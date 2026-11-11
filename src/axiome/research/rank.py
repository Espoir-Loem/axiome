"""Okapi BM25 ranking of sentences against a query (integer-free of randomness).

Floats are used for scores only; ties and output order are resolved by explicit
keys (score rounded to 1e-9, then document order), so results are deterministic.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from axiome.perception.normalize import fold, words

K1 = 1.5
B = 0.75
SCORE_DIGITS = 9


def terms(text: str, stopwords: Iterable[str] = ()) -> list[str]:
    stop = set(stopwords)
    return [w for w in words(fold(text)) if w not in stop and len(w) > 1]


@dataclass(frozen=True, slots=True)
class Ranked:
    index: int  # position in the input
    score: float


def bm25(query: str, passages: Sequence[str], stopwords: Iterable[str] = ()) -> list[Ranked]:
    stop = list(stopwords)
    q = terms(query, stop)
    docs = [terms(p, stop) for p in passages]
    if not docs or not q:
        return []
    n = len(docs)
    avg = sum(len(d) for d in docs) / n or 1.0
    df = Counter(t for d in docs for t in set(d))
    out: list[Ranked] = []
    for i, d in enumerate(docs):
        tf = Counter(d)
        score = 0.0
        for t in q:
            if not tf[t]:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * len(d) / avg))
        if score > 0:
            out.append(Ranked(i, round(score, SCORE_DIGITS)))
    return sorted(out, key=lambda r: (-r.score, r.index))


def overlap(a: str, b: str, stopwords: Iterable[str] = ()) -> int:
    """Shared content words, in percent of the smaller sentence (integer)."""
    stop = list(stopwords)
    ta, tb = set(terms(a, stop)), set(terms(b, stop))
    if not ta or not tb:
        return 0
    return (100 * len(ta & tb)) // min(len(ta), len(tb))
