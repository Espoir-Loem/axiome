"""Interface texte d'Axiome (REPL et commande unique)."""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Callable, Sequence

from axiome import __version__
from axiome.core.clock import FixedClock
from axiome.core.config import IN_MEMORY, Config
from axiome.core.errors import AxiomeError
from axiome.kernel import Kernel
from axiome.response import render

HELP = """\
Commandes :
  fait(a, b).                 ajouter un fait (statut initial : NON VÉRIFIÉ)
  tete(X) :- corps(X).        ajouter une règle (hypothèse)
  ?- requete(X, b).           interroger (conjonctions et « non » permis)
  :preuve fait(a, b)          expliquer pourquoi (arbre de preuve + statuts)
  :conflits                   contradictions détectées et leur résolution
  :sources                    sources connues
  :regles                     programme logique actif
  :aide                       cette aide
  :quitter                    sortir
"""


def _rules(k: Kernel) -> str:
    program = k.program()
    lines = [str(r) + ("" if r.axiomatic else "   % hypothèse") for r in program.rules]
    lines += [str(c) for c in program.constraints]
    return "\n".join(lines)


COMMANDS: dict[str, Callable[[Kernel, str], str]] = {
    ":aide": lambda k, a: HELP,
    ":preuve": lambda k, a: render.render_explanation(k.explain(a)),
    ":conflits": lambda k, a: render.render_conflicts(k.state),
    ":sources": lambda k, a: render.render_sources(k.store.sources()),
    ":regles": lambda k, a: _rules(k),
}


def execute(kernel: Kernel, line: str) -> str:
    """Exécute une ligne et renvoie la réponse (fonction pure vis-à-vis de l'E/S)."""
    line = line.strip()
    if not line:
        return ""
    if line.startswith(":"):
        name, _, arg = line.partition(" ")
        handler = COMMANDS.get(name)
        if handler is None:
            return f"Commande inconnue : {name} (tapez :aide)"
        return handler(kernel, arg.strip())
    if line.startswith("?-"):
        return render.render_query(kernel.ask(line))
    return kernel.tell(line)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="axiome", description="IA neuro-symbolique déterministe.")
    p.add_argument("--version", action="version", version=f"axiome {__version__}")
    p.add_argument("--db", help="chemin de la base (défaut : $AXIOME_DB ou XDG)")
    p.add_argument("--memoire", action="store_true", help="base éphémère en mémoire")
    p.add_argument(
        "-c",
        "--commande",
        action="append",
        default=[],
        help="exécute une ligne puis quitte (répétable)",
    )
    return p


def _safe_execute(kernel: Kernel, line: str) -> tuple[str, bool]:
    """Exécute une ligne ; renvoie (sortie, succès). Les bogues ne sont pas masqués."""
    try:
        return execute(kernel, line), True
    except AxiomeError as exc:
        return f"Erreur : {exc}", False


def _config(args: argparse.Namespace) -> Config:
    if args.memoire:
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
    print(f"Axiome {__version__} — tapez :aide")
    while True:
        try:
            line = input("axiome> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in (":quitter", ":q"):
            return 0
        out, _ = _safe_execute(kernel, line)
        if out:
            print(out)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if isinstance(sys.stdout, io.TextIOWrapper):  # consoles Windows (cp1252) : forcer UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
    # En mode commande, l'horloge est figée : la sortie est reproductible à l'octet près.
    kernel = Kernel.open(_config(args), FixedClock() if args.commande else None)
    return _run_commands(kernel, args.commande) if args.commande else _repl(kernel)


if __name__ == "__main__":
    sys.exit(main())
