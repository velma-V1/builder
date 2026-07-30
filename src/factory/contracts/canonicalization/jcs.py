from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import rfc8785

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode, JsonValue


def _to_plain_json(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError(ErrorCode.PARSE_REJECTED, "mapping keys must be strings")
            result[key] = _to_plain_json(item)
        return result
    if isinstance(value, Sequence):
        return [_to_plain_json(item) for item in value]
    message = f"unsupported value type for canonicalization: {type(value)!r}"
    raise ContractError(ErrorCode.PARSE_REJECTED, message)


def _freeze(value: JsonValue) -> JsonValue:
    # Runtime consumers receive MappingProxyType/tuple structures for immutability. These are
    # not themselves JSON values (RFC 8785 bytes are computed separately, before freezing), so
    # the cast below is a deliberate escape from the JsonValue union for the frozen runtime form.
    if isinstance(value, dict):
        frozen_mapping = {key: _freeze(item) for key, item in value.items()}
        return cast(JsonValue, MappingProxyType(frozen_mapping))
    if isinstance(value, list):
        return cast(JsonValue, tuple(_freeze(item) for item in value))
    return value


@dataclass(frozen=True, slots=True)
class Canonicalized:
    canonical_bytes: bytes
    content_hash: str
    document: Mapping[str, JsonValue]


def canonicalize(document: Mapping[str, JsonValue]) -> Canonicalized:
    plain = _to_plain_json(document)
    if not isinstance(plain, dict):
        message = "a contract document must canonicalize to a JSON object"
        raise ContractError(ErrorCode.PARSE_REJECTED, message)

    try:
        canonical_bytes = rfc8785.dumps(plain)
    except rfc8785.CanonicalizationError as exc:
        raise ContractError(ErrorCode.PARSE_REJECTED, f"canonicalization rejected: {exc}") from exc

    content_hash = hashlib.sha256(canonical_bytes).hexdigest()
    frozen_document = _freeze(plain)
    assert isinstance(frozen_document, Mapping)
    return Canonicalized(
        canonical_bytes=canonical_bytes, content_hash=content_hash, document=frozen_document
    )
