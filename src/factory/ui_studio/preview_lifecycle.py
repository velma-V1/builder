"""Preview lifecycle: dry-run install/start plan + a legal-transition preview session state machine.

No preview server is ever started here — :func:`build_preview_lifecycle` reuses the dry-run-by-
default installer framework, and :class:`PreviewSession` only ever moves between states via
:func:`transition`, which rejects any move not in :data:`_LEGAL_TRANSITIONS`.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.preinstall.installer import Installer, InstallStep
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import PreviewState

_LEGAL_TRANSITIONS: frozenset[tuple[PreviewState, str, PreviewState]] = frozenset(
    {
        (PreviewState.DRAFT, "render", PreviewState.RENDERING),
        (PreviewState.RENDERING, "render_ok", PreviewState.READY),
        (PreviewState.RENDERING, "render_failed", PreviewState.FAILED),
        (PreviewState.READY, "expire", PreviewState.EXPIRED),
        (PreviewState.FAILED, "retry", PreviewState.DRAFT),
        (PreviewState.EXPIRED, "retry", PreviewState.DRAFT),
    }
)


@dataclass(frozen=True, slots=True)
class PreviewSession:
    session_id: str
    state: PreviewState = PreviewState.DRAFT


def transition(session: PreviewSession, event: str) -> PreviewSession:
    for from_state, ev, to_state in _LEGAL_TRANSITIONS:
        if from_state is session.state and ev == event:
            return PreviewSession(session.session_id, to_state)
    raise UIStudioError(
        UIStudioErrorCode.PREVIEW_TRANSITION_ILLEGAL,
        f"no legal transition for event {event!r} from state {session.state.value}",
    )


def build_preview_lifecycle() -> Installer:
    """Dry-run install/start plan for a future preview server. No host action performed here."""
    steps = (
        InstallStep("inspect", "inspect current preview environment (read-only)", mutating=False),
        InstallStep("prepare", "prepare rendered artifact + config (read-only)", mutating=False),
        InstallStep(
            "start_later",
            "start an isolated preview server",
            mutating=True,
            rollback="stop the preview server and remove its process/network",
        ),
        InstallStep(
            "stop_later",
            "stop the preview server",
            mutating=True,
            rollback="restart the preview server from the last rendered artifact",
        ),
    )
    return Installer("ui_studio_preview", steps)
