# GetItDone Python SDK (`getitdone-sdk`)

The official Python SDK for the [GetItDone](https://nowgetitdone.com) API — AI-native task
management for people and agents.

All 37 `/v1` operations, fully typed (`py.typed`), **sync and async**, on `httpx`. Automatic
retries, automatic `Idempotency-Key` handling, cursor auto-pagination, a typed RFC 9457 error
hierarchy, and a Standard Webhooks verifier.

## Install

```bash
pip install getitdone-sdk
```

Requires Python 3.10+. The distribution is published as **`getitdone-sdk`**, but the import
package is **`getitdone_py`** — `pip install getitdone-sdk`, then `from getitdone_py import
GetItDone`.

## Authentication

Create an organization API key at <https://app.nowgetitdone.com/settings> (API keys) and set it
as `GETITDONE_API_KEY`:

```bash
export GETITDONE_API_KEY="gid_..."
```

`/v1` is **`Authorization: Bearer` only** — the SDK sends your key that way. (The legacy
`x-api-key` header works on the old `/api/*` surface, not on `/v1`, so the SDK deliberately does
not offer it.) OAuth 2.1 access tokens work too: pass one as `api_key=`.

| Environment variable | Purpose |
|---|---|
| `GETITDONE_API_KEY` | The credential. Read when `api_key=` is not passed. |
| `GETITDONE_BASE_URL` | Override the API host. Defaults to `https://app.nowgetitdone.com`. |

## Quickstart

```python
from getitdone_py import GetItDone

with GetItDone() as client:  # reads GETITDONE_API_KEY
    task = client.tasks.create({"title": "Ship the Python SDK", "priority": "HIGH"})
    print(task["id"])  # T-123

    client.tasks.update(task["id"], {"status": "DONE"})

    for organization in client.organizations.list():
        print(organization["name"])

    usage = client.usage.retrieve()
    print(usage["plan"], usage["meters"])
```

Async — same names, same arguments:

```python
import asyncio
from getitdone_py import AsyncGetItDone


async def main():
    async with AsyncGetItDone() as client:
        task = await client.tasks.create({"title": "Ship the Python SDK"})
        async for entry in client.tasks.list_history(task["id"]):
            print(entry["id"])


asyncio.run(main())
```

### Resources

| Namespace | Operations |
|---|---|
| `client.organizations` | `list`, `retrieve` |
| `client.members` | `list` |
| `client.projects` | `list`, `retrieve`, `create` |
| `client.tasks` | `list`, `retrieve`, `create`, `update`, `archive`, `unarchive`, `list_history` |
| `client.daily_plan` | `retrieve`, `set_status`, `create_entry`, `move_entry`, `delete_entry` |
| `client.attachments` | `list`, `create_upload`, `create`, `get_download_url` |
| `client.api_keys` | `list`, `create`, `delete` |
| `client.webhook_endpoints` | `list`, `retrieve`, `create`, `update`, `delete`, `rotate_secret`, `verify`, `test_event`, `list_deliveries`, `replay_delivery`, `replay_failed` |
| `client.usage` | `retrieve` |

Webhook-endpoint operations require a **PRO or higher** plan; on a lower plan they raise
`PermissionDeniedError` with `code == "feature_not_enabled"`.

## Pagination

The nine list operations are cursor-paginated. Iterating walks every page for you, re-sending
your original query verbatim and only advancing the cursor:

```python
for task in client.tasks.list({"status": "TODO", "limit": 100}):
    print(task["title"])
```

Or drive the cursor yourself:

```python
page = client.tasks.list({"limit": 25}).page()
page.data  # this page's items
page.has_more  # is there another page?
page.next_cursor  # opaque cursor
next_page = page.get_next_page()  # None on the last page
```

The async twin is `async for task in client.tasks.list(): ...`, with `await paginator.page()`.

## Idempotency

Ten POSTs are declared idempotent by the API. For those the SDK generates an `Idempotency-Key`
**once per logical call**, so a retried request replays the stored result instead of executing
twice. Supply your own key to make a retry safe across process restarts:

```python
client.tasks.create({"title": "Weekly report"}, idempotency_key=f"weekly-{week_number}")
```

Repeating an identical call with the same key within 24 hours returns the original result. The
four non-idempotent POSTs (`verify`, `test_event`, `replay_delivery`, `replay_failed`) are
deliberate live probes and are never retried.

## Retries

Enabled by default (`max_retries=2`) for transport failures, timeouts, `408`, `429`, `5xx` — and
`409` only when an `Idempotency-Key` was sent. A `POST` without a key is **never** retried.
Backoff is `min(8s, 0.5s * 2**attempt)` with ±25% jitter; a `Retry-After` above
`max_retry_after_seconds` (default 60) aborts instead of sleeping.

## Errors

Every failure raises a subclass of `GetItDoneError`. Branch on `.code` — never on the message.

```python
from getitdone_py import GetItDone, NotFoundError, RateLimitError, APIError

try:
    task = client.tasks.retrieve("T-999")
except NotFoundError as error:
    print(error.code)  # resource_not_found
    print(error.request_id)  # quote this in support requests
except RateLimitError as error:
    print(error.retry_after, error.is_quota_exhausted)
    print(error.rate_limit.primary)
except APIError as error:
    print(error.status_code, error.code, error.detail, error.field_errors)
```

| Status | Exception | Problem codes |
|---|---|---|
| — | `APIConnectionError` | transport failure (`APIConnectionTimeoutError` on timeout) |
| 400 | `BadRequestError` | `validation_failed`, `idempotency_key_missing` |
| 401 | `AuthenticationError` | `missing_credentials`, `invalid_api_key`, `invalid_token` |
| 403 | `PermissionDeniedError` | `insufficient_scope`, `feature_not_enabled` |
| 404 | `NotFoundError` | `resource_not_found` |
| 409 | `ConflictError` | `idempotency_in_progress`, `delivery_already_pending` |
| 422 | `UnprocessableEntityError` | `idempotency_key_reused`, `webhook_url_rejected` |
| 429 | `RateLimitError` | `rate_limited`, `quota_exhausted` |
| 5xx | `InternalServerError` | `internal_error` |

`error.field_errors` carries the per-field failures on `validation_failed`. A non-JSON body (a
CDN error page) still raises a typed `APIError`, with `problem = None` and the raw text on
`.raw_body`.

## Webhooks

Verify inbound deliveries with the endpoint's `whsec_` signing secret. **Always pass the raw
request bytes** — parsing and re-serializing the body changes the bytes and invalidates the
signature.

```python
from getitdone_py.webhooks import verify_webhook


@app.post("/hooks/getitdone")
async def hook(request):
    raw = await request.body()  # bytes, exactly as received
    result = verify_webhook(
        headers=request.headers,
        raw_body=raw,
        secret=os.environ["GETITDONE_WEBHOOK_SECRET"],
    )
    if not result.valid:
        return Response(status_code=400)  # result.reason says why
    event = json.loads(raw)  # parse only AFTER verifying
    ...
```

During a secret rotation the delivery carries one signature per active secret; pass a list and
any match verifies:

```python
verify_webhook(headers=headers, raw_body=raw, secret=[current_secret, previous_secret])
```

Event types: `task.created`, `task.updated`, `task.archived`. The timestamp tolerance is ±5
minutes (`tolerance_seconds=` to override).

## Client options

```python
client = GetItDone(
    api_key="gid_...",
    base_url="https://app.nowgetitdone.com",
    timeout=60.0,
    max_retries=2,
    max_retry_after_seconds=60.0,
    default_headers={"X-My-App": "billing-sync"},
    http_client=my_httpx_client,
)
```

| Option | Default | Notes |
|---|---|---|
| `api_key` | `$GETITDONE_API_KEY` | Sent as `Authorization: Bearer`. |
| `base_url` | `$GETITDONE_BASE_URL` or `https://app.nowgetitdone.com` | Trailing slashes stripped. |
| `timeout` | `60.0` | Per attempt, in seconds. |
| `max_retries` | `2` | Retries after the first attempt. |
| `max_retry_after_seconds` | `60.0` | A larger `Retry-After` aborts rather than sleeps. |
| `default_headers` | `{}` | Merged into every request; cannot override `Authorization`. |
| `http_client` | new `httpx.Client` | Inject your own for proxying or connection pooling. The SDK does not close a client it did not create. |

Per-call overrides go through `RequestOptions`:

```python
from getitdone_py import RequestOptions

client.tasks.list(options=RequestOptions(timeout=5.0, max_retries=0, headers={"X-Trace": "abc"}))
```

The SDK always sends `User-Agent: getitdone-sdk/<version>`. Do not remove it — the API's edge
rejects default Python user agents with `403 error code: 1010`.

Escape hatch for anything not yet wrapped:

```python
data = client.request("GET", "/v1/tasks", query={"limit": 5})
```

### Logging

The SDK logs to the standard `getitdone_py` logger. Request/response events are `DEBUG`, retries
are `WARNING`; credential headers are redacted and bodies are never logged.

```python
import logging

logging.getLogger("getitdone_py").setLevel(logging.DEBUG)
```

## Development

```bash
pip install -e ".[dev]"
pytest tests --ignore=tests/e2e     # unit tests
ruff check . && ruff format --check . && ty check
```

`src/getitdone_py/models.py` is **generated** from `openapi/v1.json` and must never be hand-edited
— CI fails on any diff. To refresh both:

```bash
GETITDONE_MONOREPO=/path/to/GetItDone bash scripts/sync-spec.sh
bash scripts/regenerate-models.sh
```

The webhook signature vectors in `tests/fixtures/webhook_vectors.json` are produced by importing
the TypeScript signer from the app monorepo, which is what proves cross-language compatibility:

```bash
GETITDONE_MONOREPO=/path/to/GetItDone \
  node scripts/generate-webhook-vectors.mjs > tests/fixtures/webhook_vectors.json
```

The tests in `tests/e2e/` run against production. Two of them need no credentials; the rest skip
loudly unless `GETITDONE_API_KEY` is set.

## License

MIT © 2026 Devino Solutions Inc.
