"""The ONE request engine every SDK method rides.

A line-for-line port of ``packages/sdk/src/core/http.ts`` in the GetItDone
monorepo, in both a sync and an async flavour.

Retry contract (pinned by ``tests/unit/test_retry.py``):

* Retried failures: transport errors, per-attempt timeouts, HTTP 408, 429
  (honoring ``Retry-After``), 5xx — and 409 ONLY when an ``Idempotency-Key``
  was sent (the API's only 409 is ``idempotency_in_progress``, which resolves
  to a replay once the first execution finishes).
* A ``POST`` is NEVER retried without an ``Idempotency-Key``. Every
  consequential POST in the /v1 registry is declared idempotent, and for those
  the SDK auto-generates a key ONCE, before the attempt loop, so every retry
  replays instead of re-executing. ``GET``/``PATCH``/``DELETE`` are
  retry-eligible: /v1 PATCHes are absolute-set and DELETE converges.
* A ``Retry-After`` above ``max_retry_after_seconds`` (default 60) aborts
  retrying — a burst window is worth waiting for, a billing period is not.

Auth is ``Authorization: Bearer`` ONLY. ``x-api-key`` is a legacy ``/api/*``
scheme that /v1 rejects with ``401 missing_credentials``, so it is deliberately
not offered. The ``User-Agent`` is mandatory: Cloudflare answers default Python
user agents with ``403 error code: 1010`` before the request reaches the app.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import quote

import httpx

from getitdone_py.errors import (
    APIConnectionError,
    APIConnectionTimeoutError,
    APIError,
    build_api_error,
    parse_problem,
    parse_retry_after_seconds,
)

HttpMethod = Literal["GET", "POST", "PATCH", "DELETE"]

RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

#: Header values that are never logged.
REDACTED_HEADERS = frozenset({"authorization", "x-api-key", "cookie", "set-cookie"})

logger = logging.getLogger("getitdone_py")


def encode_path_param(value: str) -> str:
    """Percent-encode a path segment (``T-1/2`` must not become two segments)."""
    return quote(str(value), safe="")


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Copy of ``headers`` with credential values replaced by ``<redacted>``."""
    return {
        key: ("<redacted>" if key.lower() in REDACTED_HEADERS else value)
        for key, value in headers.items()
    }


def backoff_seconds(attempt: int, rng: random.Random | None = None) -> float:
    """``min(8s, 0.5s * 2**attempt)`` with +/-25% jitter."""
    base = min(8.0, 0.5 * 2**attempt)
    jitter = (rng or random).random()
    return base * (0.75 + jitter * 0.5)


def is_retryable_status(status: int, idempotency_key_sent: bool) -> bool:
    if status == 409:
        return idempotency_key_sent
    return status in RETRYABLE_STATUSES or status >= 500


def build_query(query: dict[str, Any] | None) -> list[tuple[str, str | int | float | None]]:
    """Flatten a query mapping, dropping ``None`` and expanding sequences."""
    if not query:
        return []
    out: list[tuple[str, str | int | float | None]] = []
    for key, value in query.items():
        if value is None:
            continue
        values = value if isinstance(value, (list, tuple, set)) else [value]
        for entry in values:
            if entry is None:
                continue
            if isinstance(entry, bool):
                out.append((key, "true" if entry else "false"))
            else:
                out.append((key, str(entry)))
    return out


@dataclass
class RequestOptions:
    """Per-request overrides accepted by every resource method."""

    #: Explicit ``Idempotency-Key``. On idempotent-declared POSTs the SDK
    #: generates one automatically when this is omitted.
    idempotency_key: str | None = None
    timeout: float | None = None
    max_retries: int | None = None
    #: Extra headers merged last — they can never override ``Authorization``.
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class RequestParams:
    method: HttpMethod
    #: Interpolated path, e.g. ``/v1/tasks/T-12``.
    path: str
    query: dict[str, Any] | None = None
    body: Any = None
    #: Descriptor-declared consequential POST — opts this call into
    #: ``Idempotency-Key`` auto-generation.
    idempotent: bool = False
    options: RequestOptions | None = None


@dataclass
class APIResponse:
    """Full-fidelity result: parsed data plus the transport metadata."""

    data: Any
    status_code: int
    headers: dict[str, str]
    request_id: str | None

    @property
    def replayed(self) -> bool:
        """True when the API replayed a stored idempotent result (24 h window)."""
        return self.headers.get("idempotency-replayed", "").lower() == "true"


@dataclass
class _Prepared:
    url: str
    params: list[tuple[str, str | int | float | None]]
    headers: dict[str, str]
    body: Any
    idempotency_key: str | None
    retry_eligible: bool
    max_retries: int
    timeout: float


class _CoreBase:
    """Shared request planning for the sync and async transports."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        max_retries: int,
        max_retry_after_seconds: float,
        user_agent: str,
        default_headers: dict[str, str] | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_retry_after_seconds = max_retry_after_seconds
        self.user_agent = user_agent
        self.default_headers = dict(default_headers or {})

    def _prepare(self, params: RequestParams) -> _Prepared:
        options = params.options or RequestOptions()
        max_retries = options.max_retries if options.max_retries is not None else self.max_retries
        timeout = options.timeout if options.timeout is not None else self.timeout

        # Computed ONCE, before the attempt loop: a retried request must present
        # the SAME key so the server replays instead of re-executing.
        idempotency_key = options.idempotency_key
        if idempotency_key is None and params.idempotent:
            idempotency_key = f"gid-sdk-{uuid.uuid4()}"

        headers: dict[str, str] = {
            "accept": "application/json",
            "user-agent": self.user_agent,
            **{k.lower(): v for k, v in self.default_headers.items()},
            **{k.lower(): v for k, v in options.headers.items()},
        }
        # Auth is set LAST — per-request headers cannot override it with a
        # stale credential by accident.
        headers["authorization"] = f"Bearer {self.api_key}"
        if params.body is not None:
            headers["content-type"] = "application/json"
        if idempotency_key is not None:
            headers["idempotency-key"] = idempotency_key

        return _Prepared(
            url=f"{self.base_url}{params.path}",
            params=build_query(params.query),
            headers=headers,
            body=params.body,
            idempotency_key=idempotency_key,
            retry_eligible=params.method != "POST" or idempotency_key is not None,
            max_retries=max_retries,
            timeout=timeout,
        )

    def _evaluate(
        self,
        params: RequestParams,
        prepared: _Prepared,
        response: httpx.Response,
        attempt: int,
    ) -> tuple[APIResponse | None, APIError | None, float | None]:
        """Return ``(success, error, retry_delay)`` for one completed attempt."""
        headers = {key.lower(): value for key, value in response.headers.items()}
        request_id = headers.get("x-request-id")

        if response.is_success:
            data: Any = None
            if response.status_code != 204 and response.content:
                try:
                    data = response.json()
                except ValueError:
                    data = response.text
            return (
                APIResponse(
                    data=data,
                    status_code=response.status_code,
                    headers=headers,
                    request_id=request_id,
                ),
                None,
                None,
            )

        raw_body = response.text
        error = build_api_error(
            status_code=response.status_code,
            headers=headers,
            request_id=request_id,
            problem=parse_problem(raw_body),
            raw_body=raw_body or None,
            method=params.method,
            url=prepared.url,
        )

        retry_after = parse_retry_after_seconds(headers.get("retry-after"))
        can_retry = (
            prepared.retry_eligible
            and attempt < prepared.max_retries
            and is_retryable_status(response.status_code, prepared.idempotency_key is not None)
            and (retry_after is None or retry_after <= self.max_retry_after_seconds)
        )
        if not can_retry:
            return None, error, None

        delay = retry_after if retry_after is not None else backoff_seconds(attempt)
        logger.warning(
            "getitdone-py retrying request",
            extra={
                "method": params.method,
                "path": params.path,
                "status": response.status_code,
                "attempt": attempt + 1,
                "max_retries": prepared.max_retries,
                "delay_seconds": round(delay, 3),
                "request_id": request_id,
            },
        )
        return None, error, delay

    def _connection_error(
        self, exc: Exception, prepared: _Prepared
    ) -> APIConnectionError | APIConnectionTimeoutError:
        if isinstance(exc, httpx.TimeoutException):
            return APIConnectionTimeoutError(f"Request timed out after {prepared.timeout}s.")
        return APIConnectionError("Connection error.", cause=exc)

    def _log_request(self, params: RequestParams, prepared: _Prepared) -> None:
        logger.debug(
            "getitdone-py request",
            extra={
                "method": params.method,
                "url": prepared.url,
                "headers": redact_headers(prepared.headers),
            },
        )


class HttpCore(_CoreBase):
    """Synchronous transport."""

    def __init__(self, *, http_client: httpx.Client | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client()

    def request(self, params: RequestParams) -> Any:
        return self.request_with_response(params).data

    def request_with_response(self, params: RequestParams) -> APIResponse:
        prepared = self._prepare(params)
        attempt = 0
        while True:
            self._log_request(params, prepared)
            try:
                response = self._client.request(
                    params.method,
                    prepared.url,
                    params=prepared.params or None,
                    headers=prepared.headers,
                    json=prepared.body,
                    timeout=prepared.timeout,
                )
            except httpx.HTTPError as exc:
                error = self._connection_error(exc, prepared)
                if prepared.retry_eligible and attempt < prepared.max_retries:
                    time.sleep(backoff_seconds(attempt))
                    attempt += 1
                    continue
                raise error from exc

            success, api_error, delay = self._evaluate(params, prepared, response, attempt)
            if success is not None:
                return success
            if delay is None:
                assert api_error is not None
                raise api_error
            time.sleep(delay)
            attempt += 1

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class AsyncHttpCore(_CoreBase):
    """Asynchronous transport — identical semantics, ``asyncio.sleep`` backoff."""

    def __init__(self, *, http_client: httpx.AsyncClient | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient()

    async def request(self, params: RequestParams) -> Any:
        return (await self.request_with_response(params)).data

    async def request_with_response(self, params: RequestParams) -> APIResponse:
        prepared = self._prepare(params)
        attempt = 0
        while True:
            self._log_request(params, prepared)
            try:
                response = await self._client.request(
                    params.method,
                    prepared.url,
                    params=prepared.params or None,
                    headers=prepared.headers,
                    json=prepared.body,
                    timeout=prepared.timeout,
                )
            except httpx.HTTPError as exc:
                error = self._connection_error(exc, prepared)
                if prepared.retry_eligible and attempt < prepared.max_retries:
                    await asyncio.sleep(backoff_seconds(attempt))
                    attempt += 1
                    continue
                raise error from exc

            success, api_error, delay = self._evaluate(params, prepared, response, attempt)
            if success is not None:
                return success
            if delay is None:
                assert api_error is not None
                raise api_error
            await asyncio.sleep(delay)
            attempt += 1

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
