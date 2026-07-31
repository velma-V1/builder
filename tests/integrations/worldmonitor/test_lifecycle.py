"""WorldMonitor lifecycle — dry-run by default (no mutation), isolation posture declared."""

from __future__ import annotations

from factory.integrations.worldmonitor import FUTURE_ISOLATION, LIFECYCLE_PHASES, build_lifecycle
from factory.preinstall.installer import StepOutcome


def test_lifecycle_phases_declared() -> None:
    assert LIFECYCLE_PHASES[0] == "inspect"
    assert "install_later" in LIFECYCLE_PHASES
    assert "rollback_later" in LIFECYCLE_PHASES


def test_lifecycle_default_run_is_dry_run_no_mutation() -> None:
    report = build_lifecycle().run()  # default: dry-run
    assert not report.mutated
    mutating = [r for r in report.results if r.outcome is StepOutcome.SKIPPED_DRY_RUN]
    assert mutating  # the *_later phases are mutating and were skipped
    # every mutating phase declares a rollback (plan shows no MISSING rollback)
    assert "(MISSING)" not in build_lifecycle().format_plan()


def test_future_isolation_posture_is_hardened() -> None:
    iso = FUTURE_ISOLATION
    assert iso.read_only_rootfs and iso.non_root
    assert iso.no_host_networking and iso.no_docker_socket
    assert iso.dedicated_network and iso.egress_via_broker_only
    assert iso.approved_volumes_only and iso.bounded_cpu_ram
