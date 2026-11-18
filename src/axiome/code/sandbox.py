"""Confined execution of untrusted code (M7.2).

This is the only module of the code tools allowed to start a process. The
rules of RFC-0002 are applied literally:

* the repository is copied to a temporary directory, removed afterwards; the
  user's working tree is never modified;
* the child runs with a wall-clock timeout, ``resource`` limits (CPU, memory,
  file size, no core dump) and a capped report;
* the environment is rebuilt from scratch: no ``AXIOME_*`` variable, no
  secret, no proxy survives; ``PYTHONHASHSEED=0`` and ``TZ=UTC`` make runs
  reproducible;
* the network is cut with ``unshare -n`` when the platform allows it. When it
  does not, the report says ``degraded_network``: nothing is silently claimed
  to be isolated.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Any

from axiome.code.source import IGNORED_DIRECTORIES
from axiome.core.errors import CodeError

MEGABYTE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    """Hard ceilings for one sandboxed run."""

    timeout_seconds: float = 30.0
    cpu_seconds: int = 10
    memory_bytes: int = 512 * MEGABYTE
    file_bytes: int = 10 * MEGABYTE
    output_bytes: int = 64 * 1024


@dataclass(frozen=True, slots=True)
class SandboxResult:
    """What happened, without ever leaking the environment."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    truncated: bool = False
    network_isolated: bool = False
    degraded_network: bool = False

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def report(self) -> str:
        """A short, deterministic summary for the user."""
        status = "passed" if self.passed else ("timeout" if self.timed_out else "failed")
        network = "isolated" if self.network_isolated else "not isolated"
        return f"{status} (exit {self.returncode}, network {network})"


def run(
    root: str | Path,
    command: Sequence[str],
    limits: SandboxLimits | None = None,
    *,
    isolate_network: bool = True,
    overlay: Mapping[str, str] | None = None,
) -> SandboxResult:
    """Run ``command`` in a temporary copy of ``root`` and report the outcome.

    ``overlay`` writes files into the copy only (used by the generation search);
    the original tree is never touched.
    """
    settings = limits or SandboxLimits()
    source = Path(root)
    if not source.is_dir():
        raise CodeError("code.not_a_directory", path=str(root))
    with tempfile.TemporaryDirectory(prefix="axiome-sandbox-") as temporary:
        work = Path(temporary) / "tree"
        shutil.copytree(source, work, ignore=_ignore)
        _write_overlay(work, overlay or {})
        return _execute(work, command, settings, isolate_network)


def run_tests(
    root: str | Path,
    targets: Sequence[str] = (),
    limits: SandboxLimits | None = None,
    *,
    isolate_network: bool = True,
    overlay: Mapping[str, str] | None = None,
) -> SandboxResult:
    """Run the project's tests (pytest) in the sandbox; all of them by default."""
    command = [sys.executable, "-m", "pytest", "-q", *targets]
    return run(root, command, limits, isolate_network=isolate_network, overlay=overlay)


def _write_overlay(work: Path, overlay: Mapping[str, str]) -> None:
    root = work.resolve()
    for relative, text in overlay.items():
        target = (work / relative).resolve()
        if not target.is_relative_to(root):
            raise CodeError("code.outside_repository", path=relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _execute(
    work: Path, command: Sequence[str], limits: SandboxLimits, isolate_network: bool
) -> SandboxResult:
    isolated = isolate_network and _can_unshare()
    prefix = ["unshare", "-n"] if isolated else []
    process = subprocess.Popen(
        [*prefix, *command],
        cwd=work,
        env=_environment(work),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # The child immediately execs; no Python thread can exist in it yet.
        preexec_fn=_limiter(limits) if os.name == "posix" else None,  # noqa: PLW1509
    )
    timed_out = False
    try:
        out, err = process.communicate(timeout=limits.timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        out, err = process.communicate()
    stdout, truncated_out = _decode(out, limits.output_bytes)
    stderr, truncated_err = _decode(err, limits.output_bytes)
    return SandboxResult(
        process.returncode if process.returncode is not None else -1,
        stdout,
        stderr,
        timed_out=timed_out,
        truncated=truncated_out or truncated_err,
        network_isolated=isolated,
        degraded_network=isolate_network and not isolated,
    )


def _decode(data: bytes | None, cap: int) -> tuple[str, bool]:
    raw = data or b""
    truncated = len(raw) > cap
    return raw[:cap].decode("utf-8", errors="replace"), truncated


#: Windows needs these to start a process at all; none of them carries a
#: secret. SystemRoot is required by subprocess (side-by-side assemblies).
_WINDOWS_ESSENTIALS = (
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
)


def _environment(work: Path) -> dict[str, str]:
    """A clean environment: no AXIOME_*, no proxy, no secret, fixed seeds."""
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        # The copy must shadow an editable install of this very package, otherwise
        # the project's tests would measure the working tree instead of the copy.
        "PYTHONPATH": os.pathsep.join((str(work / "src"), str(work))),
        "HOME": str(work),
        "TMPDIR": str(work),
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TZ": "UTC",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "SOURCE_DATE_EPOCH": "0",
    }
    if os.name == "nt":
        for name in _WINDOWS_ESSENTIALS:
            value = os.environ.get(name)
            if value:
                environment[name] = value
        environment["TEMP"] = str(work)
        environment["TMP"] = str(work)
    return environment


def _limiter(limits: SandboxLimits) -> Callable[[], None]:
    """Return a ``preexec_fn`` applying POSIX resource limits in the child."""

    def apply() -> None:
        # Imported dynamically: typeshed describes ``resource`` as POSIX-only,
        # so a direct import fails mypy on Windows even inside a guarded call.
        resource: Any = import_module("resource")

        for kind, value in (
            (resource.RLIMIT_CPU, limits.cpu_seconds),
            (resource.RLIMIT_AS, limits.memory_bytes),
            (resource.RLIMIT_FSIZE, limits.file_bytes),
            (resource.RLIMIT_CORE, 0),
        ):
            try:
                _soft, hard = resource.getrlimit(kind)
                ceiling = value if hard == resource.RLIM_INFINITY else min(value, hard)
                resource.setrlimit(kind, (ceiling, ceiling))
            except (OSError, ValueError):
                # Some limits, notably RLIMIT_AS on macOS, are unsupported.
                # Skipping one must not abort a run that is otherwise confined.
                continue

    return apply


def _ignore(directory: str, names: list[str]) -> set[str]:
    """Skip caches, virtual environments and build outputs when copying."""
    del directory
    return {
        name
        for name in names
        if name in IGNORED_DIRECTORIES or name.endswith(".egg-info") or name == ".coverage"
    }


@cache
def _can_unshare() -> bool:
    """True if ``unshare -n`` actually works on this machine (cached once)."""
    executable = shutil.which("unshare")
    if executable is None:
        return False
    try:
        probe = subprocess.run(
            [executable, "-n", "true"], capture_output=True, timeout=2, check=False
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - platform dependent
        return False
    return probe.returncode == 0
