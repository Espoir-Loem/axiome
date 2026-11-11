"""Researcher: queries web providers in parallel and digests what they return.

Checklist: providers run concurrently under a time budget; results are consumed
in the configured provider order (never completion order) so the stream is
deterministic; a failing provider is skipped, never fatal; every excerpt kept is
a verbatim sentence of a source.
"""

from __future__ import annotations

import concurrent.futures as cf
import re
import time
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass

from axiome.core.errors import ResearchError
from axiome.dialogue.events import Event, Searching, SourceFound
from axiome.perception.normalize import fold, words
from axiome.research.extract import sentences
from axiome.research.providers.base import Document, SearchProvider
from axiome.research.rank import bm25, overlap, terms
from axiome.verification.epistemic import Assessment, Evidence, Source, Stance, assess

RESULTS_PER_PROVIDER = 3
SENTENCES_PER_DOCUMENT = 25
BUDGET_S = 10.0
AGREEMENT_PERCENT = 50  # content-word overlap for two sentences to say the same thing
AMBIGUITY_WINDOW = 300  # a disambiguation page says so in its first words
LEAD_BONUS = 0.5  # the opening sentence of a summary is usually the definition


@dataclass(frozen=True, slots=True)
class Excerpt:
    doc: int  # index of the document it comes from
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class WebFindings:
    """What the web says, organized like an answer: lead, details, references."""

    documents: tuple[Document, ...]
    lead: Excerpt | None  # the sentence that answers the question
    points: tuple[Excerpt, ...]  # further details, in reading order
    agreeing: tuple[Source, ...]  # independent sources saying the same as the lead
    see_also: tuple[str, ...]  # other pages of the main site (other senses, related topics)
    assessment: Assessment | None

    @property
    def cited(self) -> tuple[int, ...]:
        """Documents cited, in order of first citation (numbering of the references)."""
        order: list[int] = []
        for excerpt in (self.lead, *self.points):
            if excerpt is not None and excerpt.doc not in order:
                order.append(excerpt.doc)
        return tuple(order)


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

    def active(self, deep: bool) -> tuple[SearchProvider, ...]:
        """Providers for this search: deep ones (scholarly...) only in deep research."""
        return tuple(p for p in self.providers if deep or not getattr(p, "deep", False))

    def search(
        self, query: str, language: str, deep: bool = False
    ) -> Generator[Event, None, list[Document]]:
        """Yield progress events; return the documents (in provider order)."""
        docs: list[Document] = []
        chosen = self.active(deep)
        if not chosen:
            return docs
        for provider in chosen:
            yield Searching(provider.name, query)
        deadline = time.monotonic() + self.budget_s
        pool = cf.ThreadPoolExecutor(max_workers=len(chosen))
        try:
            futures = [pool.submit(p.search, query, language, self.per_provider) for p in chosen]
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


def _definition(query: str, sents: Sequence[str], stop: Sequence[str]) -> str | None:
    """On the page named like the question, the first sentence naming it is the definition."""
    wanted = set(terms(query, stop))
    for text in sents:
        if wanted & set(terms(text, stop)):
            return text
    return None


def _best_per_document(
    query: str, split: Sequence[Sequence[str]], stop: Sequence[str]
) -> dict[int, Excerpt]:
    passages = [(d, pos, text) for d, sents in enumerate(split) for pos, text in enumerate(sents)]
    best: dict[int, Excerpt] = {}
    for r in bm25(query, [p[2] for p in passages], stop):
        d, pos, text = passages[r.index]
        score = round(r.score * (1 + LEAD_BONUS / (1 + pos)), 9)
        if d not in best or score > best[d].score:
            best[d] = Excerpt(d, text, score)
    return best


def _novel(text: str, chosen: Iterable[Excerpt], stop: Sequence[str]) -> bool:
    return all(overlap(text, c.text, stop) < AGREEMENT_PERCENT for c in chosen)


def is_ambiguous(doc: Document, pattern: re.Pattern[str]) -> bool:
    """A disambiguation page ("X may refer to:") lists meanings and defines nothing."""
    return bool(pattern.search(fold(doc.text[:AMBIGUITY_WINDOW])))


def _drop_ambiguous(
    wanted: list[str],
    docs: Sequence[Document],
    best: dict[int, Excerpt],
    pattern: re.Pattern[str] | None,
) -> tuple[dict[int, Excerpt], tuple[str, ...]]:
    """Remove disambiguation pages. If the page named like the question is one, the
    question itself is ambiguous: the other titles are returned as its meanings."""
    if pattern is None:
        return best, ()
    named = [d for d, doc in enumerate(docs) if words(fold(doc.title)) == wanted]
    if any(is_ambiguous(docs[d], pattern) for d in named):
        others = (d.title for d in docs if d.title and words(fold(d.title)) != wanted)
        return {}, tuple(dict.fromkeys(others))
    return {d: e for d, e in best.items() if not is_ambiguous(docs[d], pattern)}, ()


def digest(
    query: str,
    docs: Sequence[Document],
    stopwords: Iterable[str] = (),
    *,
    details: int = 3,
    corroborations: int = 2,
    ambiguous: re.Pattern[str] | None = None,
) -> WebFindings:
    """Choose the main page, its key sentence, the details and the agreeing sources.

    The main page is the first one titled exactly like the question (search
    engines rank the canonical page first), otherwise the page holding the best
    ranked sentence. Other pages of the same site are listed as "see also";
    pages from other organizations corroborate or add details.
    """
    stop = list(stopwords)
    docs = tuple(docs)
    split = [sentences(d.text)[:SENTENCES_PER_DOCUMENT] for d in docs]
    best = _best_per_document(query, split, stop)
    wanted = words(fold(query))
    best, meanings = _drop_ambiguous(wanted, docs, best, ambiguous)
    if meanings or not best:
        return WebFindings(docs, None, (), (), meanings, None)
    titled = [d for d in best if words(fold(docs[d].title)) == wanted]
    main = min(titled) if titled else max(best, key=lambda d: (best[d].score, -d))
    definition = _definition(query, split[main], stop) if titled else None
    lead = Excerpt(main, definition, best[main].score) if definition else best[main]

    chosen = [lead]
    for text in split[main]:  # the main page, in reading order
        if len(chosen) > details:
            break
        if _novel(text, chosen, stop):
            chosen.append(Excerpt(main, text, 0.0))
    site = docs[main].source.organization
    agreeing = [docs[main].source]
    extra: list[Excerpt] = []
    see_also: list[str] = []
    for d, doc in enumerate(docs):
        if d == main:
            continue
        if doc.source.organization == site:
            if doc.title and doc.title not in (*see_also, docs[main].title):
                see_also.append(doc.title)
        elif d in best and not _novel(best[d].text, [lead], stop):
            if doc.source.organization not in {s.organization for s in agreeing}:
                agreeing.append(doc.source)
        elif (
            d in best and len(extra) < corroborations and _novel(best[d].text, chosen + extra, stop)
        ):
            extra.append(best[d])
    evidence = [Evidence(s, Stance.SUPPORTS, lead.text) for s in agreeing]
    return WebFindings(
        docs, lead, (*chosen[1:], *extra), tuple(agreeing), tuple(see_also), assess(evidence)
    )
