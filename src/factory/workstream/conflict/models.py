"""Value objects for conflict detection beyond files (``01D §3.3-3.4``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ConflictKind(StrEnum):
    FILE = "FILE"
    MODULE = "MODULE"
    SYMBOL = "SYMBOL"
    SCHEMA = "SCHEMA"
    API = "API"
    MIGRATION = "MIGRATION"
    CONFIG = "CONFIG"
    DEPENDENCY = "DEPENDENCY"
    GENERATED = "GENERATED"
    LOGICAL = "LOGICAL"


@dataclass(frozen=True, slots=True)
class Conflict:
    kind: ConflictKind
    left: str
    right: str
    detail: str


@dataclass(frozen=True, slots=True)
class ChangeManifest:
    """One workstream's declared change surface across every conflict dimension."""

    workstream_id: str
    files: frozenset[str] = frozenset()
    modules: frozenset[str] = frozenset()
    symbols: frozenset[str] = frozenset()
    schemas: frozenset[str] = frozenset()
    apis: frozenset[str] = frozenset()
    generated: frozenset[str] = frozenset()
    logical_invariants: frozenset[str] = frozenset()
    migrations: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    config: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    dependencies: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class IntegrationBaseline:
    """An immutable per-stage integration baseline (``01D §3.3``)."""

    stage_id: str
    commit: str
