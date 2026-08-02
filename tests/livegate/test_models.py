"""Stage-3 unit — readiness value types."""

from __future__ import annotations

from factory.livegate.models import CheckStatus, ReadinessCheck, ReadinessReport


def _check(status: CheckStatus, *, mandatory: bool) -> ReadinessCheck:
    return ReadinessCheck("id", "title", status, "detail", mandatory=mandatory)


def test_mandatory_non_pass_is_blocking() -> None:
    assert _check(CheckStatus.FAIL, mandatory=True).is_blocking_failure
    assert _check(CheckStatus.UNAVAILABLE, mandatory=True).is_blocking_failure
    assert not _check(CheckStatus.PASS, mandatory=True).is_blocking_failure


def test_advisory_never_blocks() -> None:
    assert not _check(CheckStatus.FAIL, mandatory=False).is_blocking_failure
    assert not _check(CheckStatus.UNAVAILABLE, mandatory=False).is_blocking_failure


def test_report_ready_only_when_no_blocking_failures() -> None:
    ready = ReadinessReport(
        "env", (_check(CheckStatus.PASS, mandatory=True), _check(CheckStatus.FAIL, mandatory=False))
    )
    assert ready.ready and ready.blocking_failures == ()
    not_ready = ReadinessReport("env", (_check(CheckStatus.FAIL, mandatory=True),))
    assert not not_ready.ready and len(not_ready.blocking_failures) == 1


def test_by_status_filters() -> None:
    report = ReadinessReport(
        "env",
        (
            _check(CheckStatus.PASS, mandatory=True),
            _check(CheckStatus.UNAVAILABLE, mandatory=False),
        ),
    )
    assert len(report.by_status(CheckStatus.PASS)) == 1
    assert len(report.by_status(CheckStatus.UNAVAILABLE)) == 1
    assert report.by_status(CheckStatus.ERROR) == ()
