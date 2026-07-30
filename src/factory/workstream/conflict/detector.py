"""Conflict detection beyond files (``01D §3.4``).

Before parallel admission and again before integration, pairwise-compare workstream change manifests
across every dimension. File-path disjointness alone is never proof of independence — module,
symbol, schema, API, migration, config, dependency, generated-output, and logical-invariant
conflicts are all detected and block integration.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from factory.workstream.conflict.models import ChangeManifest, Conflict, ConflictKind

# Set-valued dimensions: an intersection between two manifests is a conflict of that kind.
_SET_DIMENSIONS: tuple[tuple[str, ConflictKind], ...] = (
    ("files", ConflictKind.FILE),
    ("modules", ConflictKind.MODULE),
    ("symbols", ConflictKind.SYMBOL),
    ("schemas", ConflictKind.SCHEMA),
    ("apis", ConflictKind.API),
    ("generated", ConflictKind.GENERATED),
    ("logical_invariants", ConflictKind.LOGICAL),
)


def _pair_conflicts(a: ChangeManifest, b: ChangeManifest) -> list[Conflict]:
    found: list[Conflict] = []
    for attr, kind in _SET_DIMENSIONS:
        shared = getattr(a, attr) & getattr(b, attr)
        if shared:
            found.append(
                Conflict(kind, a.workstream_id, b.workstream_id, f"{attr}: {sorted(shared)}")
            )

    a_mig = dict(a.migrations)
    b_mig = dict(b.migrations)
    dup_ids = set(a_mig) & set(b_mig)
    order_clash = {o for o in a_mig.values()} & {o for o in b_mig.values()}
    if dup_ids or order_clash:
        detail = f"ids={sorted(dup_ids)}; orders={sorted(order_clash)}"
        found.append(Conflict(ConflictKind.MIGRATION, a.workstream_id, b.workstream_id, detail))

    a_cfg = dict(a.config)
    b_cfg = dict(b.config)
    cfg_clash = {k for k in set(a_cfg) & set(b_cfg) if a_cfg[k] != b_cfg[k]}
    if cfg_clash:
        found.append(
            Conflict(
                ConflictKind.CONFIG, a.workstream_id, b.workstream_id, f"keys={sorted(cfg_clash)}"
            )
        )

    a_dep = dict(a.dependencies)
    b_dep = dict(b.dependencies)
    dep_clash = {d for d in set(a_dep) & set(b_dep) if a_dep[d] != b_dep[d]}
    if dep_clash:
        found.append(
            Conflict(
                ConflictKind.DEPENDENCY, a.workstream_id, b.workstream_id,
                f"deps={sorted(dep_clash)}",
            )
        )
    return found


class ConflictDetector:
    """Pairwise conflict detection across a set of workstream change manifests."""

    def detect(self, manifests: Sequence[ChangeManifest]) -> tuple[Conflict, ...]:
        conflicts: list[Conflict] = []
        for a, b in combinations(manifests, 2):
            conflicts.extend(_pair_conflicts(a, b))
        return tuple(conflicts)

    def is_independent(self, manifests: Sequence[ChangeManifest]) -> bool:
        return not self.detect(manifests)
