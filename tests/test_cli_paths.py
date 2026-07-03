"""Tests for shared CLI path containment validation (scripts/cli_paths.py)."""

import argparse
from pathlib import Path

import pytest

import cli_paths

SYSTEM_TMP = Path("/tmp")  # NOSONAR -- boundary under test; nothing is written


def test_accepts_path_inside_repo() -> None:
    inside = cli_paths.REPO_ROOT / "distributions" / "schema.sql"
    assert cli_paths.contained_path(str(inside)) == inside


def test_accepts_path_inside_system_temp_dir(tmp_path: Path) -> None:
    target = tmp_path / "combined-data.nt"
    assert cli_paths.contained_path(str(target)) == target.resolve()


@pytest.mark.skipif(not SYSTEM_TMP.exists(), reason="no /tmp on this platform")
def test_accepts_literal_tmp_path() -> None:
    resolved = cli_paths.contained_path(str(SYSTEM_TMP / "combined-data.nt"))
    assert resolved == SYSTEM_TMP.resolve() / "combined-data.nt"


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


def test_rejects_symlink_pointing_outside_allowed_roots() -> None:
    link = cli_paths.REPO_ROOT / "test-escape-symlink"
    link.symlink_to(Path.home() / "nonexistent-target")
    link_str = str(link)
    try:
        with pytest.raises(ValueError, match="outside"):
            cli_paths.contained_path(link_str)
    finally:
        link.unlink()


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
