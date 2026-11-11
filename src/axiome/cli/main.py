"""Axiome text interface (REPL and single-command mode)."""

from __future__ import annotations

import argparse
import io
import re
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import replace

from axiome import __version__
from axiome.core.clock import FixedClock
from axiome.core.config import IN_MEMORY, Config
from axiome.core.errors import AxiomeError, ResearchError
from axiome.dialogue import layout
from axiome.dialogue.session import Session
from axiome.i18n import SUPPORTED, get_locale, set_locale, t
from axiome.kernel import Kernel
from axiome.knowledge.wikidata import Librarian
from axiome.research.setup import build_librarian, build_researcher
from axiome.response import render

QUIT = (":quit", ":q")
# A logic statement starts with "?-" or with "predicate(" (fact or rule).
_LOGIC = re.compile(r"^\s*(?:\?-|[a-z_][A-Za-z0-9_]*\()")


def is_logic(line: str) -> bool:
    return bool(_LOGIC.match(line))


def converse(session: Session, line: str, *, color: bool = False) -> Iterator[str]:
    """Render the event stream of one turn as text chunks, as soon as they come."""
    return layout.chunks(session.respond(line), color=color)


def _rules(k: Kernel) -> str:
    program = k.program()
    suffix = f"   % {t('cli.hypothesis')}"
    lines = [str(r) + ("" if r.axiomatic else suffix) for r in program.rules]
    lines += [str(c) for c in program.constraints]
    return "\n".join(lines)


COMMANDS: dict[str, Callable[[Kernel, str], str]] = {
    ":help": lambda k, a: t("cli.help"),
    ":proof": lambda k, a: render.render_explanation(k.explain(a)),
    ":conflicts": lambda k, a: render.render_conflicts(k.state),
    ":sources": lambda k, a: render.render_sources(k.store.sources()),
    ":rules": lambda k, a: _rules(k),
}


def execute(kernel: Kernel, line: str) -> str:
    """Run one line and return the output (pure with respect to I/O)."""
    line = line.strip()
    if not line:
        return ""
    if line.startswith(":"):
        name, _, arg = line.partition(" ")
        handler = COMMANDS.get(name)
        if handler is None:
            return t("cli.unknown_command", name=name)
        return handler(kernel, arg.strip())
    if line.startswith("?-"):
        return render.render_query(kernel.ask(line))
    return str(kernel.tell(line))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="axiome", description=t("cli.description"))
    p.add_argument("--version", action="version", version=f"axiome {__version__}")
    p.add_argument("--db", help=t("cli.opt_db"))
    p.add_argument("--memory", action="store_true", help=t("cli.opt_memory"))
    p.add_argument("--offline", action="store_true", help=t("cli.opt_offline"))
    p.add_argument("--lang", choices=SUPPORTED, default=None, help=t("cli.opt_lang"))
    p.add_argument("-c", "--command", action="append", default=[], help=t("cli.opt_command"))
    p.add_argument("--learn", action="append", default=[], help=t("cli.opt_learn"))
    return p


def _safe_execute(kernel: Kernel, line: str) -> tuple[str, bool]:
    """Run a line; return (output, success). Bugs are not swallowed."""
    try:
        return execute(kernel, line), True
    except AxiomeError as exc:
        return t("cli.error", message=exc), False


def _config(args: argparse.Namespace) -> Config:
    config = Config.from_env()
    if args.memory:
        config = replace(config, db_path=IN_MEMORY)
    elif args.db:
        config = replace(config, db_path=args.db)
    if args.offline:
        config = replace(config, offline=True)
    return config


def _handle(session: Session, line: str, color: bool) -> bool:
    """Process one line, streaming its output; return False on an expected error."""
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(":") or is_logic(stripped):
        out, ok = _safe_execute(session.kernel, stripped)
        if out:
            print(out)
        return ok
    try:
        for chunk in converse(session, stripped, color=color):
            print(chunk, end="", flush=True)
    except AxiomeError as exc:
        print(t("cli.error", message=exc))
        return False
    return True


def _run_commands(session: Session, lines: Sequence[str]) -> int:
    status = 0
    for line in lines:
        status = status if _handle(session, line, color=False) else 1
    return status


def _repl(session: Session) -> int:
    print(t("cli.banner", version=__version__))
    color = sys.stdout.isatty()
    while True:
        try:
            line = input("axiome> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in QUIT:
            return 0
        _handle(session, line, color)


def _learn(librarian: Librarian | None, topics: Sequence[str], language: str) -> int:
    """``--learn``: import topics from Wikidata ahead of time, then answer offline."""
    if librarian is None:
        print(t("cli.learn_offline"))
        return 1
    failed = 0
    for topic in topics:
        try:
            done = librarian.learn(topic, language)
        except ResearchError as exc:
            print(t("cli.learn_failed", topic=topic, detail=exc))
            failed += 1
            continue
        if done.concept is None:
            print(t("cli.learn_unknown", topic=topic))
            failed += 1
            continue
        counts = {"concepts": len(done.concepts), "facts": done.facts, "words": done.words}
        print(t("cli.learned", topic=topic, concept=done.concept, **counts))
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    previous = get_locale()
    if args.lang:
        set_locale(args.lang)
    if isinstance(sys.stdout, io.TextIOWrapper):  # Windows consoles (cp1252): force UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        # In command mode the clock is frozen, so output is byte-for-byte reproducible.
        config = _config(args)
        kernel = Kernel.open(config, FixedClock() if args.command else None)
        librarian = build_librarian(config, kernel)
        if args.learn:
            return _learn(librarian, args.learn, get_locale())
        session = Session(kernel, researcher=build_researcher(config), librarian=librarian)
        return _run_commands(session, args.command) if args.command else _repl(session)
    finally:
        set_locale(previous)


if __name__ == "__main__":
    sys.exit(main())
