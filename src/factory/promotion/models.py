from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum


class PromotionOutcome(StrEnum):
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class PromotionBinding:
    task_id: str
    run_id: str
    evidence_digest: str
    manifest_digest: str
    target_ref: str
    target_revision: str

    def scope(self) -> str:
        return json.dumps(
            {
                "evidence_digest": self.evidence_digest,
                "manifest_digest": self.manifest_digest,
                "run_id": self.run_id,
                "target_ref": self.target_ref,
                "target_revision": self.target_revision,
                "task_id": self.task_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True, slots=True)
class PromotionRecord:
    promotion_id: str
    task_id: str
    run_id: str
    approval_card_id: str
    decided_by: str
    promoted_branch: str | None
    promoted_commit_sha: str | None
    outcome: PromotionOutcome
    reason: str
    created_at: str
