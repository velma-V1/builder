"""PH-6 — simulated three-workstream demonstration (IP-3), wiring PH-4/PH-5 fakes."""

from __future__ import annotations

from factory.integration import run_simulated_ip3


def test_simulated_ip3_end_to_end() -> None:
    report = run_simulated_ip3()
    # Three independent workstreams admitted; a fourth is denied by the ≤3 cap.
    assert report.admitted == ("WS1", "WS2", "WS3")
    assert report.fourth_denied is True
    # Each lane got an isolated checkout, a fake sandbox, and a fake route.
    assert report.checkouts_isolated is True
    assert len(report.sandbox_ids) == 3 and len(set(report.sandbox_ids)) == 3
    assert all(route for route in report.routes)
    # No conflicts; the coordinator integrates without editing source.
    assert report.conflicts == 0
    assert report.integration_verdict == "INTEGRATED"
    assert report.promoted == ("WS1", "WS2", "WS3")
    assert set(report.final_lane_states) == {"INTEGRATED"}
    assert report.coordinator_edits_source is False
