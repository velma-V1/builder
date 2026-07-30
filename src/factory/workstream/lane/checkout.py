"""Isolated checkout assignment (``01D §2.8/§6.5-6``).

Every concurrently active lane modifying the same repository gets its own isolated checkout (a Git
worktree id here); a branch alone is not sufficient workspace isolation. The assigner guarantees a
distinct checkout per lane so cross-lane workspace contamination is impossible.
"""

from __future__ import annotations

from factory.workstream.errors import WorkstreamError


class IsolatedCheckoutAssigner:
    """Assigns and tracks one isolated checkout per lane."""

    __slots__ = ("_by_lane", "_seq")

    def __init__(self) -> None:
        self._by_lane: dict[str, str] = {}
        self._seq = 0

    def assign(self, lane_id: str, repo_id: str) -> str:
        if lane_id in self._by_lane:
            raise WorkstreamError(
                "CHECKOUT_ALREADY_ASSIGNED", f"lane {lane_id} already has a checkout"
            )
        self._seq += 1
        checkout_id = f"wt-{repo_id}-{self._seq}"
        self._by_lane[lane_id] = checkout_id
        return checkout_id

    def checkout_for(self, lane_id: str) -> str | None:
        return self._by_lane.get(lane_id)

    def is_isolated(self) -> bool:
        """True iff no two lanes share a checkout id (workspace isolation invariant)."""
        ids = list(self._by_lane.values())
        return len(ids) == len(set(ids))
