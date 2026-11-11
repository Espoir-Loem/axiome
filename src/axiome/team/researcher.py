"""Researcher: queries web providers in parallel and digests what they return.

Checklist: providers run concurrently under a time budget; results are consumed
in the configured provider order (never completion order) so the stream is
deterministic; a failing provider is skipped, never fatal; every excerpt kept is
a verbatim sentence of a source.
"""

from __future__ import annotations

import concurrent.futures as cf
import time
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass

from axiome.core.errors import ResearchError
from axiome.dialogue.events import Event, Searching, SourceFound
from axiome.perception.normalize import fold, words
from axiome.research.extract import sentences
from axiome.research.providers.base import Document, SearchProvider
from axiome.research.rank import bm25, overlap
from axiome.verification.epistemic import Assessment, Evidence, Source, Stance, assess

RESULTS_PER_PROVIDER = 3
SENTENCES_PER_DOCUMENT = 25
BUDGET_S = 10.0
AGREEMENT_PERCENT = 50  # content-word overlap for two sentences to say the same thing
LEAD_BONUS = 0.5  # the opening sentence of a summary is usually the definition
TITLE_BONUS = 2.0  # a page titled exactly like the question is the page about it


@dataclass(frozen=True, slots=True)
class Excerpt:
    source: Source
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class WebFindings:
    summary: Excerpt | None
    agreeing: tuple[Source, ...]  # sources (summary's included) that say the same thing
    others: tuple[Excerpt, ...]  # best sentence of each other source
    assessment: Assessment | None


class Researcher:
    def __init__(
        self,
        providers: Sequence[SearchProvider],
        per_provider: int = RESULTS_PER_PROVIDER,
        budget_s: float = BUDGET_S,
    ) -> None:
        self.providers = tuple(providers)
        self.per_provider = per_provider
        self.budget_s = budget_s

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.providers]

    def search(self, query: str, language: str) -> Generator[Event, None, list[Document]]:
        """Yield progress events; return the documents (in provider order)."""
        docs: list[Document] = []
        if not self.providers:
            return docs
        for provider in self.providers:
            yield Searching(provider.name, query)
        deadline = time.monotonic() + self.budget_s
        pool = cf.ThreadPoolExecutor(max_workers=len(self.providers))
        try:
            futures = [
                pool.submit(p.search, query, language, self.per_provider) for p in self.providers
            ]
            for future in futures:
                try:
                    found = future.result(timeout=max(0.0, deadline - time.monotonic()))
                except (ResearchError, cf.TimeoutError):
                    continue
                for doc in found:
                    docs.append(doc)
                    yield SourceFound(doc.source)
        finally:  # never wait for a provider past the budget
            pool.shutdown(wait=False, cancel_futures=True)
        return docs


def digest(query: str, docs: Sequence[Document], stopwords: Iterable[str] = ()) -> WebFindings:
    """Pick the best sentence, find which independent sources agree with it."""
    stop = list(stopwords)
    passages: list[tuple[int, int, str]] = []  # (document, position, sentence)
    for d, doc in enumerate(docs):
        for pos, sentence in enumerate(sentences(doc.text)[:SENTENCES_PER_DOCUMENT]):
            passages.append((d, pos, sentence))
    ranked = bm25(query, [p[2] for p in passages], stop)
    wanted = words(fold(query))
    titled = {d for d, doc in enumerate(docs) if words(fold(doc.title)) == wanted}
    best: dict[int, Excerpt] = {}
    order: list[tuple[float, int, int]] = []
    for r in ranked:
        d, pos, text = passages[r.index]
        bonus = TITLE_BONUS if d in titled else 1.0
        score = round(r.score * bonus * (1 + LEAD_BONUS / (1 + pos)), 9)
        order.append((-score, d, r.index))
        if d not in best or score > best[d].score:
            best[d] = Excerpt(docs[d].source, text, score)
    if not best:
        return WebFindings(None, (), (), None)
    top_doc = min(order)[1]
    summary = best[top_doc]
    agreeing = [summary.source]
    others: list[Excerpt] = []
    for d in sorted(best):
        if d == top_doc:
            continue
        excerpt = best[d]
        if overlap(excerpt.text, summary.text, stop) >= AGREEMENT_PERCENT:
            agreeing.append(excerpt.source)
        else:
            others.append(excerpt)
    evidence = [Evidence(s, Stance.SUPPORTS, summary.text) for s in agreeing]
    return WebFindings(summary, tuple(agreeing), tuple(others), assess(evidence))
