from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from factory.contracts.activation.store import _SQLiteActivationWriter
from factory.contracts.cache.runtime_cache import RuntimeContractCache
from factory.contracts.errors import ContractError
from factory.contracts.models import (
    ActivationRecord,
    CacheEntry,
    CanonicalContract,
    ErrorCode,
    ImpactResult,
    JsonValue,
    PolicyDecision,
    PolicyOutcome,
)


def _to_json(value: object) -> str:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = dataclasses.asdict(value)
    return json.dumps(value, default=str)


@dataclass(slots=True)
class ActivationService:
    writer: _SQLiteActivationWriter
    cache: RuntimeContractCache

    def activate(
        self,
        candidate: CanonicalContract,
        *,
        impact: ImpactResult,
        policy: PolicyDecision,
        evidence: Mapping[str, JsonValue],
        expected_generation: int,
        approval_record: Mapping[str, JsonValue] | None = None,
        rollback_contract_version: int | None = None,
    ) -> ActivationRecord:
        if not candidate.validation.valid:
            raise ContractError(ErrorCode.SCHEMA_REJECTED, "candidate is not validated")

        recomputed_hash = hashlib.sha256(candidate.canonical_bytes).hexdigest()
        if recomputed_hash != candidate.content_hash:
            message = "candidate content hash is not stable before activation"
            raise ContractError(ErrorCode.CACHE_QUARANTINED, message)

        if policy.outcome is PolicyOutcome.DENY_SECURITY_VIOLATION:
            raise ContractError(ErrorCode.SECURITY_DENIED, "activation denied by policy")
        if policy.outcome is PolicyOutcome.HUMAN_APPROVAL_REQUIRED and approval_record is None:
            raise ContractError(
                ErrorCode.APPROVAL_REQUIRED, "human approval is required before activation"
            )

        record = self.writer.activate_transactionally(
            project_id=candidate.project_id,
            contract_id=candidate.contract_id,
            contract_version=candidate.version,
            schema_version=candidate.schema_version,
            content_hash=candidate.content_hash,
            canonical_json=candidate.canonical_bytes,
            validation_report_json=_to_json(candidate.validation),
            impact_report_json=_to_json(impact),
            policy_decision_json=_to_json(policy),
            evidence_json=_to_json(dict(evidence)),
            expected_generation=expected_generation,
            rollback_contract_version=rollback_contract_version,
        )

        entry = CacheEntry(
            record=record, canonical_bytes=candidate.canonical_bytes, document=candidate.document
        )
        try:
            self.cache.publish(entry)
        except Exception:
            self.cache.quarantine(
                candidate.project_id, candidate.contract_id, "cache publish failed after commit"
            )
            self.cache.publish(entry)

        return record

    def rollback(
        self,
        *,
        project_id: str,
        contract_id: str,
        target_version: int,
        expected_generation: int,
        reason: str,
    ) -> ActivationRecord:
        record = self.writer.rollback_transactionally(
            project_id=project_id,
            contract_id=contract_id,
            target_version=target_version,
            expected_generation=expected_generation,
            reason=reason,
        )
        # The rolled-back-to document isn't available here (only SQLite metadata is), so the
        # safest action is to quarantine rather than publish a stale/guessed cache entry; the
        # next `RuntimeContractCache.get()` call will fail closed with CACHE_QUARANTINED until
        # a caller republishes it from the actual canonical bytes of the target version.
        self.cache.quarantine(
            project_id, contract_id, reason=f"rolled back to v{target_version}: {reason}"
        )
        return record
