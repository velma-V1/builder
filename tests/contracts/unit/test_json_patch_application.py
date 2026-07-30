from types import MappingProxyType

import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.service import (
    _apply_add,
    _apply_change_operations,
    _apply_remove,
    _apply_replace,
    _list_index,
    _navigate_parent,
    _parse_pointer,
    _thaw,
)


def test_thaw_converts_frozen_mapping_and_tuple_to_plain_dict_and_list() -> None:
    frozen = MappingProxyType({"a": (1, 2, MappingProxyType({"b": 3}))})
    result = _thaw(frozen)
    assert result == {"a": [1, 2, {"b": 3}]}
    assert isinstance(result["a"], list)
    assert isinstance(result["a"][2], dict)


def test_thaw_rejects_unsupported_type() -> None:
    with pytest.raises(ContractError) as raised:
        _thaw(object())
    assert raised.value.code is ErrorCode.SEMANTIC_REJECTED


def test_parse_pointer_handles_root_and_escaping() -> None:
    assert _parse_pointer("") == []
    assert _parse_pointer("/a~1b/c~0d") == ["a/b", "c~d"]


def test_parse_pointer_rejects_missing_leading_slash() -> None:
    with pytest.raises(ContractError):
        _parse_pointer("no-leading-slash")


def test_list_index_append_marker_only_valid_for_insert() -> None:
    assert _list_index("-", 3, for_insert=True) == 3
    with pytest.raises(ContractError):
        _list_index("-", 3, for_insert=False)


def test_list_index_rejects_non_digit_token() -> None:
    with pytest.raises(ContractError):
        _list_index("abc", 3, for_insert=False)


def test_list_index_rejects_out_of_range() -> None:
    with pytest.raises(ContractError):
        _list_index("5", 3, for_insert=False)
    with pytest.raises(ContractError):
        _list_index("-1", 3, for_insert=False)


def test_navigate_parent_traverses_nested_structures() -> None:
    document = {"a": [{"b": "value"}]}
    parent = _navigate_parent(document, ["a", "0", "b"])
    assert parent == {"b": "value"}


def test_navigate_parent_rejects_missing_dict_key() -> None:
    with pytest.raises(ContractError):
        _navigate_parent({"a": {}}, ["a", "missing", "x"])


def test_navigate_parent_rejects_traversal_through_scalar() -> None:
    with pytest.raises(ContractError):
        _navigate_parent({"a": "scalar"}, ["a", "b", "c"])


def test_apply_add_to_dict_list_and_append() -> None:
    document: dict[str, object] = {"items": [1, 2], "obj": {}}
    _apply_add(document, ["obj", "key"], "value")
    assert document["obj"] == {"key": "value"}

    _apply_add(document, ["items", "0"], 99)
    assert document["items"] == [99, 1, 2]

    _apply_add(document, ["items", "-"], 100)
    assert document["items"] == [99, 1, 2, 100]


def test_apply_add_rejects_root_and_scalar_targets() -> None:
    with pytest.raises(ContractError):
        _apply_add({}, [], "value")
    with pytest.raises(ContractError):
        _apply_add({"a": "scalar"}, ["a", "b"], "value")


def test_apply_replace_rejects_missing_field_root_and_scalar() -> None:
    with pytest.raises(ContractError):
        _apply_replace({}, [], "value")
    with pytest.raises(ContractError):
        _apply_replace({"a": {}}, ["a", "missing"], "value")
    with pytest.raises(ContractError):
        _apply_replace({"a": "scalar"}, ["a", "b"], "value")


def test_apply_replace_on_list_index() -> None:
    document: dict[str, object] = {"items": [1, 2, 3]}
    _apply_replace(document, ["items", "1"], 99)
    assert document["items"] == [1, 99, 3]


def test_apply_remove_rejects_missing_field_root_and_scalar() -> None:
    with pytest.raises(ContractError):
        _apply_remove({}, [])
    with pytest.raises(ContractError):
        _apply_remove({"a": {}}, ["a", "missing"])
    with pytest.raises(ContractError):
        _apply_remove({"a": "scalar"}, ["a", "b"])


def test_apply_remove_from_list_and_dict() -> None:
    document: dict[str, object] = {"items": [1, 2, 3], "obj": {"key": "value"}}
    _apply_remove(document, ["items", "1"])
    assert document["items"] == [1, 3]
    _apply_remove(document, ["obj", "key"])
    assert document["obj"] == {}


def test_apply_change_operations_rejects_missing_path() -> None:
    with pytest.raises(ContractError) as raised:
        _apply_change_operations({"a": 1}, [{"op": "replace", "value": 2}])
    assert raised.value.code is ErrorCode.SEMANTIC_REJECTED


def test_apply_change_operations_rejects_unsupported_op() -> None:
    with pytest.raises(ContractError) as raised:
        _apply_change_operations({"a": 1}, [{"op": "copy", "path": "/a", "value": 2}])
    assert raised.value.code is ErrorCode.SEMANTIC_REJECTED


def test_apply_change_operations_add_and_remove_round_trip() -> None:
    document = {"a": 1, "list": [1, 2]}
    result = _apply_change_operations(
        document,
        [
            {"op": "add", "path": "/b", "value": "new"},
            {"op": "remove", "path": "/a"},
            {"op": "replace", "path": "/list/0", "value": 99},
        ],
    )
    assert result == {"b": "new", "list": [99, 2]}
