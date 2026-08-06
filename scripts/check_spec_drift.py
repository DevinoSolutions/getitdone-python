"""Compare the live published OpenAPI document against the vendored copy.

The Python analogue of the TypeScript SDK importing ``@getitdone/api-contracts``
directly: that SDK cannot drift because it consumes the contracts package at
build time, while this one vendors ``openapi/v1.json``. The nightly
``spec-drift`` workflow runs this and opens an issue when it exits non-zero.

Exit codes: 0 in sync, 1 drift detected, 2 the spec could not be fetched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDORED_PATH = REPO_ROOT / "openapi" / "v1.json"
PUBLIC_SPEC_URL = "https://nowgetitdone.com/docs/api/openapi.json"


def read_version() -> str:
    init = (REPO_ROOT / "src" / "getitdone_py" / "__init__.py").read_text(encoding="utf-8")
    for line in init.splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    return "0.0.0"


def operations(spec: dict[str, Any]) -> dict[str, str]:
    """``operationId`` -> ``"METHOD /path"``."""
    return {
        operation["operationId"]: f"{method.upper()} {path}"
        for path, item in spec.get("paths", {}).items()
        for method, operation in item.items()
        if isinstance(operation, dict) and "operationId" in operation
    }


def main() -> int:
    vendored = json.loads(VENDORED_PATH.read_text(encoding="utf-8"))

    try:
        # The custom UA is mandatory: the edge answers default Python agents
        # with `403 error code: 1010`.
        response = httpx.get(
            PUBLIC_SPEC_URL,
            headers={
                "User-Agent": f"getitdone-sdk/{read_version()}",
                "Accept": "application/json",
            },
            timeout=60.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        live = response.json()
    except Exception as error:  # noqa: BLE001 - any failure is a reportable outcome
        print(f"Could not fetch {PUBLIC_SPEC_URL}: {error!r}")
        return 2

    live_operations = operations(live)
    vendored_operations = operations(vendored)
    live_schemas = set(live.get("components", {}).get("schemas", {}))
    vendored_schemas = set(vendored.get("components", {}).get("schemas", {}))

    added = sorted(set(live_operations) - set(vendored_operations))
    removed = sorted(set(vendored_operations) - set(live_operations))
    changed = sorted(
        operation_id
        for operation_id, route in live_operations.items()
        if operation_id in vendored_operations and vendored_operations[operation_id] != route
    )
    schemas_added = sorted(live_schemas - vendored_schemas)
    schemas_removed = sorted(vendored_schemas - live_schemas)

    if not (added or removed or changed or schemas_added or schemas_removed):
        print(
            f"In sync: {len(live_operations)} operations, {len(live_schemas)} schemas "
            f"match openapi/v1.json."
        )
        return 0

    print("`openapi/v1.json` no longer matches the live published spec.\n")
    print(f"- Live: {PUBLIC_SPEC_URL}")
    print(f"- Live operations: {len(live_operations)}, vendored: {len(vendored_operations)}\n")
    for label, entries in (
        ("Operations added in production", added),
        ("Operations removed in production", removed),
        ("Operations whose method/path changed", changed),
        ("Component schemas added", schemas_added),
        ("Component schemas removed", schemas_removed),
    ):
        if entries:
            print(f"**{label}**")
            for entry in entries:
                print(f"- `{entry}`")
            print()

    print("Fix:\n")
    print("```bash")
    print(
        "bash scripts/sync-spec.sh          # or GETITDONE_MONOREPO=... bash scripts/sync-spec.sh"
    )
    print("bash scripts/regenerate-models.sh")
    print("```")
    print(
        "\nThen extend `OPERATION_MAP` in `tests/unit/test_operation_coverage.py` "
        "and add the SDK methods for any new operations."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
