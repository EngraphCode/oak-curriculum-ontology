"""Tests for shared CLI path containment validation (scripts/cli_paths.py)."""

import argparse
import tempfile
from pathlib import Path

import pytest

import cli_paths

SYSTEM_TMP = Path("/tmp")  # NOSONAR -- boundary under test; nothing is written


def test_accepts_path_inside_repo() -> None:
    inside = cli_paths.REPO_ROOT / "distributions" / "schema.sql"
    assert cli_paths.contained_path(str(inside)) == inside


def test_accepts_path_inside_system_temp_dir() -> None:
    root = cli_paths._trusted_temp_roots()[0]
    with tempfile.TemporaryDirectory(dir=root) as d:
        target = Path(d) / "combined-data.nt"
        assert cli_paths.contained_path(target) == target.resolve()

@pytest.mark.skipif(not SYSTEM_TMP.exists(), reason="no /tmp on this platform")
def test_accepts_literal_tmp_path() -> None:
    resolved = cli_paths.contained_path(str(SYSTEM_TMP / "combined-data.nt"))
    assert resolved == SYSTEM_TMP.resolve() / "combined-data.nt"


@pytest.mark.skipif(not SYSTEM_TMP.exists(), reason="no /tmp on this platform")
def test_temp_roots_not_widened_by_tmpdir_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exporting TMPDIR must not add arbitrary directories to the boundary."""
    monkeypatch.setenv("TMPDIR", "/")
    monkeypatch.setattr(tempfile, "tempdir", None)  # defeat gettempdir() caching
    roots = cli_paths._trusted_temp_roots()
    known = {
        Path(anchor).resolve()
        for anchor in cli_paths._KNOWN_TEMP_ANCHORS
        if Path(anchor).exists()
    }
    assert Path("/") not in roots
    assert set(roots) <= known


def test_normalises_dot_dot_that_stays_inside_repo() -> None:
    raw = str(cli_paths.REPO_ROOT / "scripts" / ".." / "README.md")
    assert cli_paths.contained_path(raw) == cli_paths.REPO_ROOT / "README.md"


def test_rejects_dot_dot_escape_from_repo() -> None:
    raw = str(cli_paths.REPO_ROOT / ".." / "escape.sql")
    with pytest.raises(ValueError, match="outside"):
        cli_paths.contained_path(raw)


def test_rejects_home_directory_path() -> None:
    raw = str(Path.home() / "escape.sql")
    with pytest.raises(ValueError, match="outside"):
        cli_paths.contained_path(raw)


def test_rejects_symlink_pointing_outside_allowed_roots(tmp_path: Path) -> None:
    link = tmp_path / "escape-symlink"
    link.symlink_to(Path.home() / "nonexistent-target")
    link_str = str(link)
    with pytest.raises(ValueError, match="outside"):
        cli_paths.contained_path(link_str)


def test_accepts_path_object_input() -> None:
    inside = cli_paths.REPO_ROOT / "ontology"
    assert cli_paths.contained_path(inside) == inside


def test_argparse_wrapper_raises_argument_type_error() -> None:
    raw = str(Path.home() / "escape.sql")
    with pytest.raises(argparse.ArgumentTypeError, match="outside"):
        cli_paths.contained_path_arg(raw)


def test_argparse_wrapper_passes_through_valid_path() -> None:
    inside = cli_paths.REPO_ROOT / "ontology"
    assert cli_paths.contained_path_arg(str(inside)) == inside
