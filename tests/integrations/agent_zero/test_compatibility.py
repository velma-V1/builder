"""Compatibility negotiation between Builder's contract and a reported worker version."""

from __future__ import annotations

from factory.integrations.agent_zero.compatibility import check_compatibility


def test_matching_versions_are_compatible() -> None:
    report = check_compatibility(builder_contract_version="1.2.0", worker_reported_version="1.2.0")
    assert report.compatible


def test_worker_behind_in_minor_is_compatible() -> None:
    report = check_compatibility(builder_contract_version="1.5.0", worker_reported_version="1.2.0")
    assert report.compatible


def test_worker_ahead_of_contract_is_rejected() -> None:
    report = check_compatibility(builder_contract_version="1.2.0", worker_reported_version="1.5.0")
    assert not report.compatible
    assert "newer" in report.reason


def test_different_major_version_is_rejected() -> None:
    report = check_compatibility(builder_contract_version="1.2.0", worker_reported_version="2.0.0")
    assert not report.compatible
    assert "major version mismatch" in report.reason


def test_unparseable_worker_version_is_rejected() -> None:
    report = check_compatibility(builder_contract_version="1.2.0", worker_reported_version="latest")
    assert not report.compatible
    assert "unparseable" in report.reason
