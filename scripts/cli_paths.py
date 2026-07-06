"""Containment validation for CLI path arguments.

These scripts are run by humans and automation alike (CI, LLM agents), so
every user-supplied path is resolved -- expanding ``..`` segments and
symlinks -- and checked against an allowlist of roots before any
filesystem access. This keeps faulty or malicious CLI arguments from
reading or writing arbitrary filesystem locations.

Allowed roots:

- the repository itself (inputs and distribution outputs live here)
- well-known system temp locations (``/tmp``, ``/var/tmp``, and macOS's
  ``/var/folders``; merge intermediates and CI staging live there)

The platform temp dir reported by ``tempfile.gettempdir()`` is deliberately
not trusted on POSIX: it honours TMPDIR/TMP/TEMP, so exporting e.g.
``TMPDIR=/`` would widen the boundary to the whole filesystem. It is used
only on platforms where none of the known locations exist (e.g. Windows).
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Containment boundaries only: this module never creates files here itself,
# it just permits callers to name paths under these roots.
_KNOWN_TEMP_ANCHORS = ("/tmp", "/var/tmp", "/var/folders")  # NOSONAR


def _trusted_temp_roots() -> tuple[Path, ...]:
    """Return system temp roots that are safe containment boundaries.

    Only the well-known POSIX temp locations are trusted, because
    ``tempfile.gettempdir()`` can be pointed anywhere via TMPDIR/TMP/TEMP.
    Where none of them exist (e.g. Windows), the platform default is the
    only sensible boundary and is used as-is.
    """
    candidates = (Path(anchor) for anchor in _KNOWN_TEMP_ANCHORS)
    anchors = sorted(path.resolve() for path in candidates if path.exists())
    if anchors:
        return tuple(anchors)
    return (Path(tempfile.gettempdir()).resolve(),)


ALLOWED_ROOTS: tuple[Path, ...] = (REPO_ROOT, *_trusted_temp_roots())


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
