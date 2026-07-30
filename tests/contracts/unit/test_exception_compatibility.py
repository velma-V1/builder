"""Runtime-protocol tests for repository exception classes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from factory.approval.errors import ApprovalError
from factory.audit.errors import AuditError
from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.fileops.errors import FileOpError
from factory.orchestrator.errors import OrchestratorError
from factory.permission.errors import PermissionError
from factory.safemode import SafeModeError
from factory.tools.errors import ToolError
from factory.workers.errors import WorkerEngineError

ErrorFactory = Callable[[], Exception]

ERROR_CASES: tuple[tuple[ErrorFactory, object, str, str], ...] = (
    (
        lambda: ApprovalError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "ApprovalError(code='CODE_X', message='message y')",
    ),
    (
        lambda: AuditError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "AuditError(code='CODE_X', message='message y')",
    ),
    (
        lambda: ContractError(ErrorCode.PARSE_REJECTED, "message y"),
        ErrorCode.PARSE_REJECTED,
        "PARSE_REJECTED: message y",
        (
            "ContractError(code=<ErrorCode.PARSE_REJECTED: 'PARSE_REJECTED'>, "
            "message='message y', issues=())"
        ),
    ),
    (
        lambda: FileOpError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "FileOpError(code='CODE_X', message='message y')",
    ),
    (
        lambda: OrchestratorError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "OrchestratorError(code='CODE_X', message='message y')",
    ),
    (
        lambda: PermissionError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "PermissionError(code='CODE_X', message='message y')",
    ),
    (
        lambda: SafeModeError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "SafeModeError(code='CODE_X', message='message y')",
    ),
    (
        lambda: ToolError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "ToolError(code='CODE_X', message='message y')",
    ),
    (
        lambda: WorkerEngineError("CODE_X", "message y"),
        "CODE_X",
        "CODE_X: message y",
        "WorkerEngineError('CODE_X: message y')",
    ),
)


@contextmanager
def _passthrough_context() -> Iterator[None]:
    yield


@pytest.mark.parametrize(("factory", "expected_code", "expected_str", "expected_repr"), ERROR_CASES)
def test_exception_raise_catch_traceback_and_public_representation(
    factory: ErrorFactory, expected_code: object, expected_str: str, expected_repr: str
) -> None:
    """Exception machinery must be able to update traceback state on Python 3.14."""
    error = factory()
    with pytest.raises(type(error)) as raised, _passthrough_context():
        raise error

    caught = raised.value
    assert caught.code == expected_code  # type: ignore[attr-defined]
    assert caught.message == "message y"  # type: ignore[attr-defined]
    assert caught.__traceback__ is not None
    assert str(caught) == expected_str
    assert repr(caught) == expected_repr


@pytest.mark.parametrize("factory", [case[0] for case in ERROR_CASES])
def test_exception_chaining_and_context(factory: ErrorFactory) -> None:
    """Explicit causes and implicit exception contexts must remain available."""
    cause = RuntimeError("cause")
    with pytest.raises(type(factory())) as chained:
        raise factory() from cause
    assert chained.value.__cause__ is cause

    with pytest.raises(type(factory())) as contextual:
        try:
            raise ValueError("context")
        except ValueError:
            raise factory()  # noqa: B904 - implicit context is the behavior under test
    assert isinstance(contextual.value.__context__, ValueError)
