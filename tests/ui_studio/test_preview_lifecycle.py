"""Preview lifecycle: dry-run install plan + legal-transition-only preview session state machine."""

from __future__ import annotations

import pytest

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import PreviewState
from factory.ui_studio.preview_lifecycle import (
    PreviewSession,
    build_preview_lifecycle,
    transition,
)


def test_preview_lifecycle_is_dry_run_by_default() -> None:
    report = build_preview_lifecycle().run()
    assert not report.mutated


def test_preview_lifecycle_plan_declares_a_rollback_for_every_mutating_phase() -> None:
    assert "(MISSING)" not in build_preview_lifecycle().format_plan()


def test_preview_session_starts_in_draft() -> None:
    session = PreviewSession("s1")
    assert session.state is PreviewState.DRAFT


def test_legal_transition_sequence_draft_to_ready() -> None:
    session = PreviewSession("s1")
    session = transition(session, "render")
    assert session.state is PreviewState.RENDERING
    session = transition(session, "render_ok")
    assert session.state is PreviewState.READY


def test_ready_can_expire_and_expired_can_retry_to_draft() -> None:
    session = PreviewSession("s1", state=PreviewState.READY)
    session = transition(session, "expire")
    assert session.state is PreviewState.EXPIRED
    session = transition(session, "retry")
    assert session.state is PreviewState.DRAFT


def test_illegal_transition_is_denied() -> None:
    session = PreviewSession("s1", state=PreviewState.DRAFT)
    with pytest.raises(UIStudioError) as excinfo:
        transition(session, "render_ok")  # can't skip straight to ready from draft
    assert excinfo.value.code is UIStudioErrorCode.PREVIEW_TRANSITION_ILLEGAL


def test_failed_session_can_retry_to_draft() -> None:
    session = PreviewSession("s1", state=PreviewState.FAILED)
    session = transition(session, "retry")
    assert session.state is PreviewState.DRAFT
