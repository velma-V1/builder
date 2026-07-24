import pytest

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode
from factory.contracts.parsing.yaml_parser import YamlLimits, parse_yaml_contract

pytestmark = pytest.mark.security


def test_python_object_tag_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("value: !!python/object:os.system ['echo pwned']\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_python_name_tag_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("value: !!python/name:os.system\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_binary_tag_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("value: !!binary |\n  aGVsbG8=\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_set_tag_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("value: !!set\n  ? a\n  ? b\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_explicit_timestamp_tag_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("value: !!timestamp 2026-07-24\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_merge_key_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("base: &base\n  a: 1\nderived:\n  <<: *base\n  b: 2\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_alias_bomb_exceeding_limit_is_rejected() -> None:
    limits = YamlLimits(max_aliases=4)
    lines = ["anchor: &a value"]
    lines.extend(f"ref{i}: *a" for i in range(6))
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("\n".join(lines) + "\n", limits)
    assert raised.value.code is ErrorCode.PARSE_REJECTED
    assert "alias" in raised.value.message.lower()


def test_alias_count_within_limit_is_accepted() -> None:
    limits = YamlLimits(max_aliases=4)
    lines = ["anchor: &a value"]
    lines.extend(f"ref{i}: *a" for i in range(3))
    document = parse_yaml_contract("\n".join(lines) + "\n", limits)
    assert document["ref0"] == "value"


def test_deeply_nested_sequence_exceeding_depth_is_rejected() -> None:
    limits = YamlLimits(max_depth=8)
    text = "root: " + "[" * 20 + "1" + "]" * 20 + "\n"
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract(text, limits)
    assert raised.value.code is ErrorCode.PARSE_REJECTED
    assert "nest" in raised.value.message.lower() or "depth" in raised.value.message.lower()


def test_node_count_exceeding_limit_is_rejected() -> None:
    limits = YamlLimits(max_nodes=20)
    text = "root: [" + ", ".join(str(i) for i in range(100)) + "]\n"
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract(text, limits)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_scalar_length_exceeding_limit_is_rejected() -> None:
    limits = YamlLimits(max_scalar_length=16)
    text = "value: " + ("a" * 100) + "\n"
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract(text, limits)
    assert raised.value.code is ErrorCode.PARSE_REJECTED


@pytest.mark.parametrize("literal", [".nan", ".inf", "-.inf", ".NaN", ".Inf"])
def test_non_finite_float_literals_are_rejected(literal: str) -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract(f"value: {literal}\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED


def test_malformed_yaml_is_rejected() -> None:
    with pytest.raises(ContractError) as raised:
        parse_yaml_contract("key: [unterminated\n")
    assert raised.value.code is ErrorCode.PARSE_REJECTED
