from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode, JsonValue

_STRICT_BOOL_PATTERN = re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$")

_ALLOWED_TAGS = frozenset(
    {
        "tag:yaml.org,2002:null",
        "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:int",
        "tag:yaml.org,2002:float",
        "tag:yaml.org,2002:str",
        "tag:yaml.org,2002:seq",
        "tag:yaml.org,2002:map",
    }
)

_NON_FINITE_FLOATS = frozenset(
    {
        ".nan",
        ".NaN",
        ".NAN",
        ".inf",
        ".Inf",
        ".INF",
        "-.inf",
        "-.Inf",
        "-.INF",
        "+.inf",
        "+.Inf",
        "+.INF",
    }
)


@dataclass(frozen=True, slots=True)
class YamlLimits:
    max_bytes: int = 1_048_576
    max_aliases: int = 32
    max_depth: int = 64
    max_nodes: int = 10_000
    max_scalar_length: int = 65_536


class _StrictSafeLoader(yaml.SafeLoader):
    """A SafeLoader restricted to standard, deterministic JSON-compatible tags."""


_Resolvers = list[tuple[str, re.Pattern[str]]]


def _strip_resolver(resolvers: _Resolvers, tag: str) -> _Resolvers:
    return [(candidate, pattern) for candidate, pattern in resolvers if candidate != tag]


_StrictSafeLoader.yaml_implicit_resolvers = {
    first_char: _strip_resolver(
        _strip_resolver(resolvers, "tag:yaml.org,2002:timestamp"),
        "tag:yaml.org,2002:bool",
    )
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for _first_char in ("t", "T", "f", "F"):
    _StrictSafeLoader.add_implicit_resolver(  # type: ignore[no-untyped-call]
        "tag:yaml.org,2002:bool", _STRICT_BOOL_PATTERN, [_first_char]
    )


def _construct_object_strict(
    loader: _StrictSafeLoader, node: yaml.Node, deep: bool = False
) -> JsonValue:
    if node.tag not in _ALLOWED_TAGS:
        raise ContractError(ErrorCode.PARSE_REJECTED, f"unsupported YAML tag: {node.tag}")
    return yaml.SafeLoader.construct_object(loader, node, deep=deep)  # type: ignore[no-any-return]


def _construct_float_strict(loader: _StrictSafeLoader, node: yaml.ScalarNode) -> float:
    value = loader.construct_scalar(node)
    if value.strip() in _NON_FINITE_FLOATS:
        message = f"non-finite float literal is rejected: {value!r}"
        raise ContractError(ErrorCode.PARSE_REJECTED, message)
    return float(value.replace("_", ""))


def _construct_mapping_strict(loader: _StrictSafeLoader, node: yaml.Node) -> dict[str, JsonValue]:
    if not isinstance(node, yaml.MappingNode):
        raise ContractError(ErrorCode.PARSE_REJECTED, "expected a YAML mapping node")
    mapping: dict[str, JsonValue] = {}
    for key_node, value_node in node.value:
        if key_node.tag != "tag:yaml.org,2002:str":
            raise ContractError(ErrorCode.PARSE_REJECTED, "mapping keys must be strings")
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ContractError(ErrorCode.PARSE_REJECTED, "mapping keys must be strings")
        if key in mapping:
            raise ContractError(ErrorCode.PARSE_REJECTED, f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictSafeLoader.construct_object = _construct_object_strict  # type: ignore[assignment]
_StrictSafeLoader.add_constructor("tag:yaml.org,2002:float", _construct_float_strict)
_StrictSafeLoader.add_constructor("tag:yaml.org,2002:map", _construct_mapping_strict)


def _prescan(text: str, limits: YamlLimits) -> None:
    node_count = 0
    alias_count = 0
    depth = 0
    try:
        for event in yaml.parse(text, Loader=_StrictSafeLoader):
            if isinstance(event, yaml.AliasEvent):
                alias_count += 1
                if alias_count > limits.max_aliases:
                    raise ContractError(ErrorCode.PARSE_REJECTED, "too many YAML aliases")
                continue
            if isinstance(event, yaml.MappingStartEvent | yaml.SequenceStartEvent):
                depth += 1
                if depth > limits.max_depth:
                    raise ContractError(ErrorCode.PARSE_REJECTED, "YAML nesting is too deep")
                node_count += 1
            elif isinstance(event, yaml.MappingEndEvent | yaml.SequenceEndEvent):
                depth -= 1
            elif isinstance(event, yaml.ScalarEvent):
                node_count += 1
                if len(event.value) > limits.max_scalar_length:
                    message = "YAML scalar exceeds maximum length"
                    raise ContractError(ErrorCode.PARSE_REJECTED, message)
            else:
                continue
            if node_count > limits.max_nodes:
                raise ContractError(ErrorCode.PARSE_REJECTED, "too many parsed YAML nodes")
    except yaml.YAMLError as exc:
        raise ContractError(ErrorCode.PARSE_REJECTED, f"invalid YAML: {exc}") from exc


def parse_yaml_contract(
    text: str,
    limits: YamlLimits = YamlLimits(),  # noqa: B008 -- immutable frozen-dataclass default
) -> dict[str, JsonValue]:
    if "\x00" in text:
        raise ContractError(ErrorCode.PARSE_REJECTED, "null bytes are rejected")
    if len(text.encode("utf-8")) > limits.max_bytes:
        raise ContractError(ErrorCode.PARSE_REJECTED, "input exceeds the maximum allowed size")

    _prescan(text, limits)

    try:
        document = yaml.load(text, Loader=_StrictSafeLoader)  # noqa: S506 -- restricted, tag-allowlisted loader
    except ContractError:
        raise
    except yaml.YAMLError as exc:
        raise ContractError(ErrorCode.PARSE_REJECTED, f"invalid YAML: {exc}") from exc

    if document is None:
        return {}
    if not isinstance(document, dict):
        raise ContractError(ErrorCode.PARSE_REJECTED, "a contract document must be a YAML mapping")
    return document
