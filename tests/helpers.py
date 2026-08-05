"""Shared test helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"
SPEC_PATH = Path(__file__).parent.parent / "openapi" / "v1.json"


def load_fixture(name: str) -> Any:
    """Load a committed JSON fixture by file stem."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def load_spec() -> dict[str, Any]:
    """Load the vendored OpenAPI 3.1 document."""
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def spec_operations() -> dict[str, tuple[str, str, bool, str]]:
    """Map ``operationId`` -> ``(method, path, idempotent, entitlement)``."""
    spec = load_spec()
    operations: dict[str, tuple[str, str, bool, str]] = {}
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            operations[operation["operationId"]] = (
                method.upper(),
                path,
                bool(operation.get("x-idempotent", False)),
                str(operation.get("x-entitlement", "")),
            )
    return operations
