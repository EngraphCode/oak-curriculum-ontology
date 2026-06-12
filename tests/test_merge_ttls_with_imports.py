"""End-to-end tests for the TTL merge script."""

import subprocess
import sys
from pathlib import Path

from rdflib import Graph, URIRef

REPO_ROOT = Path(__file__).parent.parent
MERGE_SCRIPT = REPO_ROOT / "scripts" / "merge_ttls_with_imports.py"


def run_merge(source: Path, output: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(MERGE_SCRIPT), str(source), "-o", str(output), "-q"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr


def test_consolidated_subject_imports_resolve() -> None:
    """Imports for subjects consolidated into another subject's files must resolve."""
    import merge_ttls_with_imports as m

    merger = m.TTLMerger(repo_root=REPO_ROOT)
    base = "https://w3id.org/uk/oak/curriculum/nationalcurriculum"
    for subject in ("biology", "combined-science", "french", "cooking-nutrition"):
        resolved = merger.resolve_import_uri(f"{base}/{subject}-programme-structure")
        assert isinstance(resolved, Path), f"{subject} import did not resolve"
        assert resolved.exists()


def test_merge_discovers_nested_files_and_skips_versions(tmp_path: Path) -> None:
    source = tmp_path / "data"
    (source / "sub").mkdir(parents=True)
    (source / "versions").mkdir()
    (source / "a.ttl").write_text(
        "<http://x/a> <http://x/p> <http://x/o1> .", encoding="utf-8"
    )
    (source / "sub" / "b.ttl").write_text(
        "<http://x/b> <http://x/p> <http://x/o2> .", encoding="utf-8"
    )
    (source / "versions" / "old.ttl").write_text(
        "<http://x/old> <http://x/p> <http://x/o3> .", encoding="utf-8"
    )

    output = tmp_path / "merged.ttl"
    run_merge(source, output)

    g = Graph()
    g.parse(output, format="turtle")
    subjects = set(g.subjects())
    assert URIRef("http://x/a") in subjects
    assert URIRef("http://x/b") in subjects
    # files under versions/ are excluded from the merge
    assert URIRef("http://x/old") not in subjects
