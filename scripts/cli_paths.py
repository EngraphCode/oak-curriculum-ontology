"""Containment validation for CLI path arguments.

These scripts are run by humans and automation alike (CI, LLM agents), so
every user-supplied path is resolved -- expanding ``..`` segments and
symlinks -- and checked against an allowlist of roots before any
filesystem access. This keeps faulty or malicious CLI arguments from
reading or writing arbitrary filesystem locations.

Allowed roots:

- the repository itself (inputs and distribution outputs live here)
- the system temporary directories (merge intermediates default to
  ``tempfile.gettempdir()``, and CI stages generated files in ``/tmp``;
  on macOS these differ, so both are allowed where present)
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Temp roots are allowed as *containment boundaries* only: this module never
# creates files there itself, it just permits callers to name paths there,
# which CI and the merge-script default already rely on (python:S5443).
_temp_roots = {Path(tempfile.gettempdir()).resolve()}
if Path("/tmp").exists():
    _temp_roots.add(Path("/tmp").resolve())

ALLOWED_ROOTS: tuple[Path, ...] = (REPO_ROOT, *sorted(_temp_roots))


def contained_path(raw: str | Path) -> Path:
    """Resolve *raw* and require it to be inside an allowed root.

    Raises ValueError if the resolved path escapes every allowed root.
    """
    resolved = Path(raw).resolve()
    for root in ALLOWED_ROOTS:
        if resolved.is_relative_to(root):
            return resolved
    allowed = " or ".join(str(root) for root in ALLOWED_ROOTS)
    raise ValueError(f"{str(raw)!r} resolves to {resolved}, outside {allowed}")


def contained_path_arg(raw: str) -> Path:
    """``argparse`` ``type=`` callback wrapping :func:`contained_path`."""
    try:
        return contained_path(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None
