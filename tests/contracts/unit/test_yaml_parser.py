import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract


def test_parses_a_simple_mapping() -> None:
    document = parse_yaml_contract("id: TASK-1\nversion: 1\n")
    assert document == {"id": "TASK-1", "version": 1}


def test_duplicate_keys_fail_closed() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("id: TASK-1\nid: TASK-2\n", YamlLimits())
    assert raised.value.code is ErrorCode.PARSE_REJECTED
    assert "duplicate key" in raised.value.message.lower()


def test_non_string_mapping_keys_are_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("1: a\n2: b\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_null_bytes_are_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("id: TASK-1\x00\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_input_larger_than_max_bytes_is_rejected() -> None:
    oversized = "id: " + ("a" * (YamlLimits().max_bytes + 10))
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract(oversized)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


@pytest.mark.parametrize("literal", ["true", "false", "True", "False", "TRUE", "FALSE"])
def test_recognized_boolean_literals_become_booleans(literal: str) -> None:
    document = parse_yaml_contract(f"flag: {literal}\n")
    assert document["flag"] is (literal.lower() == "true")


@pytest.mark.parametrize("literal", ["yes", "no", "on", "off", "Yes", "No", "ON", "OFF", "tRue"])
def test_yaml_1_1_boolean_surprises_remain_strings(literal: str) -> None:
    document = parse_yaml_contract(f"flag: {literal}\n")
    assert document["flag"] == literal


def test_timestamps_remain_strings() -> None:
    document = parse_yaml_contract("created_at: 2026-07-24T00:00:00Z\n")
    assert document["created_at"] == "2026-07-24T00:00:00Z"
    assert isinstance(document["created_at"], str)


def test_nested_structures_are_returned_as_plain_dict_and_list() -> None:
    document = parse_yaml_contract("a:\n  - 1\n  - 2\nb:\n  c: value\n")
    assert document == {"a": [1, 2], "b": {"c": "value"}}
    assert isinstance(document["a"], list)
    assert isinstance(document["b"], dict)


def test_empty_document_becomes_empty_mapping() -> None:
    assert parse_yaml_contract("") == {}


def test_non_mapping_top_level_document_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("- 1\n- 2\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED
