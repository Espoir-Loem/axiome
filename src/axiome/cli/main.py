"""Axiome text interface (REPL and single-command mode)."""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Callable, Sequence

from axiome import __version__
from axiome.core.clock import FixedClock
from axiome.core.config import IN_MEMORY, Config
from axiome.core.errors import AxiomeError
from axiome.i18n import SUPPORTED, get_locale, set_locale, t
from axiome.kernel import Kernel
from axiome.response import render

QUIT = (":quit", ":q")


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
    p.add_argument("--lang", choices=SUPPORTED, default=None, help=t("cli.opt_lang"))
    p.add_argument("-c", "--command", action="append", default=[], help=t("cli.opt_command"))
    return p


def _safe_execute(kernel: Kernel, line: str) -> tuple[str, bool]:
    """Run a line; return (output, success). Bugs are not swallowed."""
    try:
        return execute(kernel, line), True
    except AxiomeError as exc:
        return t("cli.error", message=exc), False


def _config(args: argparse.Namespace) -> Config:
    if args.memory:
        return Config(IN_MEMORY)
    if args.db:
        return Config(args.db)
    return Config.from_env()


def _run_commands(kernel: Kernel, lines: Sequence[str]) -> int:
    status = 0
    for line in lines:
        out, ok = _safe_execute(kernel, line)
        status = status if ok else 1
        if out:
            print(out)
    return status


def _repl(kernel: Kernel) -> int:
    print(t("cli.banner", version=__version__))
    while True:
        try:
            line = input("axiome> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in QUIT:
            return 0
        out, _ = _safe_execute(kernel, line)
        if out:
            print(out)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    previous = get_locale()
    if args.lang:
        set_locale(args.lang)
    if isinstance(sys.stdout, io.TextIOWrapper):  # Windows consoles (cp1252): force UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        # In command mode the clock is frozen, so output is byte-for-byte reproducible.
        kernel = Kernel.open(_config(args), FixedClock() if args.command else None)
        return _run_commands(kernel, args.command) if args.command else _repl(kernel)
    finally:
        set_locale(previous)


if __name__ == "__main__":
    sys.exit(main())
