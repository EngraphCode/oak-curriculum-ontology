"""The repository's own version strings must always agree."""

import check_version_consistency as cvc


def test_repository_versions_agree() -> None:
    versions = cvc.collect_versions()
    assert None not in versions.values(), f"version missing in: {versions}"
    assert len(set(versions.values())) == 1, f"versions disagree: {versions}"
