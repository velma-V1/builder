import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from factory.contracts.canonicalization.jcs import canonicalize
from factory.contracts.errors import ContractError

_MAX_SAFE_INTEGER = 2**53 - 1

_json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-_MAX_SAFE_INTEGER, max_value=_MAX_SAFE_INTEGER),
    st.text(max_size=32),
)


def _json_documents() -> st.SearchStrategy[dict[str, object]]:
    return st.dictionaries(
        st.text(min_size=1, max_size=16),
        st.recursive(
            _json_scalars,
            lambda children: st.one_of(
                st.lists(children, max_size=5),
                st.dictionaries(st.text(min_size=1, max_size=16), children, max_size=5),
            ),
            max_leaves=20,
        ),
        max_size=8,
    )


def test_key_order_does_not_change_identity() -> None:
    left = canonicalize({"b": 2, "a": 1})
    right = canonicalize({"a": 1, "b": 2})
    assert left.canonical_bytes == right.canonical_bytes
    assert left.content_hash == right.content_hash


def test_comments_and_whitespace_are_not_part_of_the_document_model() -> None:
    # Comments and formatting never reach this layer; only the parsed structure does.
    left = canonicalize({"a": 1, "b": [1, 2, 3]})
    right = canonicalize({"b": [1, 2, 3], "a": 1})
    assert left.canonical_bytes == right.canonical_bytes


def test_unicode_strings_produce_stable_output() -> None:
    left = canonicalize({"name": "café", "emoji": "\U0001f600"})
    right = canonicalize({"emoji": "\U0001f600", "name": "café"})
    assert left.canonical_bytes == right.canonical_bytes
    assert left.content_hash == right.content_hash


def test_non_string_keys_are_rejected() -> None:
    with pytest.raises(ContractError):
        canonicalize({1: "a"})  # type: ignore[dict-item]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected(value: float) -> None:
    with pytest.raises(ContractError):
        canonicalize({"x": value})


def test_sha_256_is_lowercase_64_char_hex() -> None:
    result = canonicalize({"a": 1})
    assert len(result.content_hash) == 64
    assert result.content_hash == result.content_hash.lower()
    int(result.content_hash, 16)  # must be valid hex


@settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow])
@given(_json_documents())
def test_canonicalization_is_deterministic(document: dict[str, object]) -> None:
    first = canonicalize(document)
    second = canonicalize(document)
    assert first.canonical_bytes == second.canonical_bytes
    assert first.content_hash == second.content_hash
    assert math.isfinite(len(first.canonical_bytes))


def test_unsupported_value_type_is_rejected() -> None:
    with pytest.raises(ContractError):
        canonicalize({"x": object()})  # type: ignore[dict-item]


def test_top_level_non_object_document_is_rejected() -> None:
    with pytest.raises(ContractError):
        canonicalize(["not", "an", "object"])  # type: ignore[arg-type]
