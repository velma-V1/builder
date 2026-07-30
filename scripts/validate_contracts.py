#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from factory.contracts.errors import ContractError
from factory.contracts.service import ContractService
from factory.contracts.validation.schema_registry import SchemaRegistry


def _discover(paths: list[Path]) -> list[Path]:
    discovered: list[Path] = []
    for path in paths:
        if path.is_dir():
            discovered.extend(sorted(path.rglob("*.yaml")))
        elif path.is_file():
            discovered.append(path)
    return discovered


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: validate_contracts.py <path> [<path> ...]", file=sys.stderr)
        return 2

    schemas = SchemaRegistry.load(Path("schemas"))
    service = ContractService(schemas)

    targets = _discover([Path(arg) for arg in argv])
    if not targets:
        print("no .yaml contracts discovered", file=sys.stderr)
        return 1

    exit_code = 0
    for target in targets:
        try:
            service.ingest(target)
        except ContractError as exc:
            exit_code = 1
            print(f"FAIL {target}: {exc}", file=sys.stderr)
        else:
            print(f"PASS {target}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
