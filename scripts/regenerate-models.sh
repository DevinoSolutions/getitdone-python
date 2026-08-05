#!/usr/bin/env bash
# Regenerate src/getitdone_py/models.py from the vendored openapi/v1.json.
#
# models.py is GENERATED and committed. Never hand-edit it: CI job
# `models-drift` re-runs this script and fails on any diff. To change a model,
# change the server's zod schema, run scripts/sync-spec.sh, then run this.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="$repo_root/src/getitdone_py/models.py"

datamodel-codegen \
  --input "$repo_root/openapi/v1.json" \
  --input-file-type openapi \
  --output "$output" \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.10 \
  --use-standard-collections \
  --use-union-operator \
  --enum-field-as-literal all \
  --use-schema-description \
  --field-constraints \
  --collapse-root-models \
  --disable-timestamp \
  --custom-file-header "# GENERATED FILE — DO NOT EDIT.
# Produced by scripts/regenerate-models.sh from openapi/v1.json (the artifact
# the GetItDone server generates from the SAME zod schemas its handlers
# validate with). Edit the server schema and re-run the script instead.
# ruff: noqa"

# Deterministic post-processing (part of the generator contract, re-applied on
# every run so `models-drift` stays a true diff gate):
#   1. `datetime.date` is aliased to `_Date` because two schemas carry a field
#      literally named `date`, and `date: date` makes pydantic raise
#      `unevaluable-type-annotation` (the field name shadows the type in the
#      class namespace).
#   2. `pattern=` is dropped from date/datetime-typed fields. zod's ISO-8601
#      string regex survives into the JSON Schema, and pydantic cannot apply a
#      string pattern to a `datetime` — it raises at import. The type already
#      enforces ISO-8601, so the constraint is redundant, not lost.
#   3. `extra='forbid'` becomes `extra='allow'`. /v1 evolves additively; a
#      forbidding model would make an older SDK crash on a NEW server field
#      instead of ignoring it. Unknown keys are kept, not dropped.
#   4. LF line endings regardless of the generating platform.
python - "$output" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8", newline="") as handle:
    text = handle.read().replace("\r\n", "\n")

text = text.replace(
    "from datetime import date, datetime",
    "from datetime import date as _Date\nfrom datetime import datetime",
)
text = re.sub(r"(?m)^(\s+\w+): date\b", r"\1: _Date", text)
text = re.sub(r"RootModel\[date\]", "RootModel[_Date]", text)
text = text.replace("extra='forbid'", "extra='allow'")

TEMPORAL_FIELD = re.compile(r"^\s+\w+: (?:datetime|_Date)(?: \| None)? = Field\($")
lines = text.split("\n")
kept: list[str] = []
in_temporal_field = False
for line in lines:
    if TEMPORAL_FIELD.match(line):
        in_temporal_field = True
        kept.append(line)
        continue
    if in_temporal_field:
        if line.lstrip().startswith("pattern="):
            continue
        if line.rstrip().endswith(")"):
            in_temporal_field = False
    kept.append(line)
text = "\n".join(kept)
text = text.replace("\r\n", "\n")

with open(path, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(text)
PY

echo "regenerate-models: wrote $output"
