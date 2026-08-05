#!/usr/bin/env bash
# Refresh the vendored OpenAPI document at openapi/v1.json.
#
# The GetItDone app monorepo is PRIVATE, so the spec is vendored here and
# committed. Two sources, in preference order:
#
#   1. GETITDONE_MONOREPO=/path/to/GetItDone  — copies
#      packages/api-contracts/openapi/v1.json byte-for-byte (the artifact CI
#      generates from the server's own zod schemas).
#   2. The public docs host — https://nowgetitdone.com/docs/api/openapi.json
#      fetched with the SDK User-Agent (Cloudflare rejects default Python /
#      curl-less UAs with `403 error code: 1010`).
#
# After syncing, ALWAYS run scripts/regenerate-models.sh and commit both files
# together: CI job `models-drift` fails if models.py does not match the spec.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$repo_root/openapi/v1.json"
version="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$repo_root/src/getitdone_py/__init__.py")"
user_agent="getitdone-py/${version}"

if [[ -n "${GETITDONE_MONOREPO:-}" ]]; then
  source_file="$GETITDONE_MONOREPO/packages/api-contracts/openapi/v1.json"
  if [[ ! -f "$source_file" ]]; then
    echo "sync-spec: $source_file not found" >&2
    exit 1
  fi
  cp "$source_file" "$target"
  echo "sync-spec: copied $source_file -> openapi/v1.json"
else
  url="${GETITDONE_SPEC_URL:-https://nowgetitdone.com/docs/api/openapi.json}"
  curl -fsSL -H "User-Agent: $user_agent" -H "Accept: application/json" "$url" -o "$target"
  echo "sync-spec: fetched $url -> openapi/v1.json"
fi

python - "$target" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    spec = json.load(handle)

operations = [
    operation["operationId"]
    for item in spec["paths"].values()
    for operation in item.values()
    if isinstance(operation, dict) and "operationId" in operation
]
print(f"sync-spec: {len(operations)} operations, {len(spec['components']['schemas'])} schemas")
PY
