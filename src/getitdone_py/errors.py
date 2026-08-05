"""Typed error hierarchy for the GetItDone public API.

Every non-2xx ``/v1`` response is an RFC 9457 ``application/problem+json`` body
carrying the stable ``code`` extension — ``code`` is the value integrations
branch on, never ``title``/``detail``. The class hierarchy mirrors the HTTP
status classes and is a 1:1 port of ``packages/sdk/src/error.ts`` in the
GetItDone monorepo.

A body that is NOT problem+json (a CDN error page, an HTML proxy interstitial,
an empty body) still raises a typed :class:`APIError` with ``problem = None``
and the raw text truncated into the message — never a JSON decode failure.
"""

from __future__ import annotations

import email.utils
import json
import math
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from getitdone_py.models import FieldError, Problem

__all__ = [
    "PROBLEM_CODES",
    "APIConnectionError",
    "APIConnectionTimeoutError",
    "APIError",
    "APIUserAbortError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "FieldError",
    "GetItDoneError",
    "InternalServerError",
    "NotFoundError",
    "PermissionDeniedError",
    "Problem",
    "ProblemCode",
    "RateLimit",
    "RateLimitError",
    "RateLimitWindow",
    "UnprocessableEntityError",
    "parse_problem",
    "parse_rate_limit",
    "parse_retry_after_seconds",
]

#: The frozen problem-code vocabulary (``packages/api-contracts/src/problems.ts``).
#: Typed as a ``Literal`` union so callers can ``match`` exhaustively; a NEW
#: server-side code (additive, allowed in v1) still arrives as a plain ``str``.
ProblemCode = Literal[
    "missing_credentials",
    "invalid_api_key",
    "invalid_token",
    "insufficient_scope",
    "feature_not_enabled",
    "validation_failed",
    "resource_not_found",
    "rate_limited",
    "quota_exhausted",
    "idempotency_key_missing",
    "idempotency_key_reused",
    "idempotency_in_progress",
    "webhook_url_rejected",
    "delivery_already_pending",
    "internal_error",
]

PROBLEM_CODES: tuple[str, ...] = (
    "missing_credentials",
    "invalid_api_key",
    "invalid_token",
    "insufficient_scope",
    "feature_not_enabled",
    "validation_failed",
    "resource_not_found",
    "rate_limited",
    "quota_exhausted",
    "idempotency_key_missing",
    "idempotency_key_reused",
    "idempotency_in_progress",
    "webhook_url_rejected",
    "delivery_already_pending",
    "internal_error",
)


class GetItDoneError(Exception):
    """Base class of every error this SDK raises."""


class APIConnectionError(GetItDoneError):
    """The request never produced an HTTP response (DNS/TLS/socket failure)."""

    def __init__(self, message: str = "Connection error.", *, cause: BaseException | None = None):
        super().__init__(message)
        self.__cause__ = cause


class APIConnectionTimeoutError(APIConnectionError):
    """The per-attempt timeout elapsed before a response arrived."""

    def __init__(self, message: str = "Request timed out."):
        super().__init__(message)


class APIUserAbortError(GetItDoneError):
    """The caller cancelled the request — never retried."""

    def __init__(self, message: str = "Request was aborted by the caller."):
        super().__init__(message)


@dataclass(frozen=True)
class RateLimitWindow:
    """One IETF draft-11 rate-limit window."""

    name: str
    limit: int | None = None
    remaining: int | None = None
    reset_seconds: int | None = None
    window_seconds: int | None = None


@dataclass(frozen=True)
class RateLimit:
    """Parsed draft-11 rate-limit headers plus the de-facto ``X-RateLimit-*`` trio.

    The bare ``RateLimit`` field and the ``X-`` trio always describe the FIRST
    window in ``RateLimit-Policy``.
    """

    windows: tuple[RateLimitWindow, ...] = ()
    limit: int | None = None
    remaining: int | None = None
    reset: int | None = None

    @property
    def primary(self) -> RateLimitWindow | None:
        return self.windows[0] if self.windows else None


@dataclass
class _ErrorFields:
    status_code: int
    request_id: str | None
    headers: dict[str, str]
    problem: Problem | None
    raw_body: str | None
    method: str | None = None
    url: str | None = None


class APIError(GetItDoneError):
    """An HTTP error response from the API."""

    def __init__(self, message: str, fields: _ErrorFields):
        super().__init__(message)
        self.status_code = fields.status_code
        #: ``x-request-id`` of the failing request — quote it in support requests.
        self.request_id = fields.request_id
        #: Response headers, lower-cased keys.
        self.response_headers = fields.headers
        #: The parsed problem document; ``None`` when the body was not problem+json.
        self.problem = fields.problem
        #: Raw response body — the escape hatch when ``problem`` is ``None``.
        self.raw_body = fields.raw_body
        self.method = fields.method
        self.url = fields.url

    @property
    def code(self) -> str | None:
        """Stable machine-readable problem code — the value to branch on."""
        return self.problem.code if self.problem is not None else None

    @property
    def problem_type(self) -> str | None:
        """Problem ``type`` URI; resolves to the docs page for this problem."""
        return self.problem.type if self.problem is not None else None

    @property
    def detail(self) -> str | None:
        return self.problem.detail if self.problem is not None else None

    @property
    def title(self) -> str | None:
        return self.problem.title if self.problem is not None else None

    @property
    def field_errors(self) -> list[FieldError]:
        """Field-level failures (present on ``validation_failed``)."""
        if self.problem is None or self.problem.errors is None:
            return []
        return list(self.problem.errors)

    @property
    def retry_after(self) -> float | None:
        """Parsed ``Retry-After`` (delay-seconds or HTTP-date), ``None`` when absent."""
        return parse_retry_after_seconds(self.response_headers.get("retry-after"))

    @property
    def rate_limit(self) -> RateLimit:
        """Rate-limit state carried on this response."""
        return parse_rate_limit(self.response_headers)


class BadRequestError(APIError):
    """400 — ``validation_failed`` | ``idempotency_key_missing``."""


class AuthenticationError(APIError):
    """401 — ``missing_credentials`` | ``invalid_api_key`` | ``invalid_token``."""


class PermissionDeniedError(APIError):
    """403 — ``insufficient_scope`` | ``feature_not_enabled`` (PRO+ gated feature)."""


class NotFoundError(APIError):
    """404 — ``resource_not_found``."""


class ConflictError(APIError):
    """409 — ``idempotency_in_progress`` | ``delivery_already_pending``."""


class UnprocessableEntityError(APIError):
    """422 — ``idempotency_key_reused`` | ``webhook_url_rejected``."""


class RateLimitError(APIError):
    """429 — two DISTINCT codes share this status.

    ``rate_limited`` is a per-key burst window (retry after
    :attr:`~APIError.retry_after`); ``quota_exhausted`` is the billing-period
    plan allowance, where retrying before the period resets is pointless.
    """

    @property
    def is_quota_exhausted(self) -> bool:
        return self.code == "quota_exhausted"


class InternalServerError(APIError):
    """5xx — ``internal_error``."""


_STATUS_TO_ERROR: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def build_api_error(
    *,
    status_code: int,
    headers: dict[str, str],
    request_id: str | None,
    problem: Problem | None,
    raw_body: str | None,
    method: str | None = None,
    url: str | None = None,
) -> APIError:
    """Construct the right :class:`APIError` subclass for a failed response."""
    if problem is not None:
        summary = f"{problem.code}: {problem.detail or problem.title}"
    elif raw_body:
        summary = raw_body[:200]
    else:
        summary = "no response body"
    suffix = f" (request_id: {request_id})" if request_id else ""
    message = f"{status_code} {summary}{suffix}"

    fields = _ErrorFields(
        status_code=status_code,
        request_id=request_id,
        headers=headers,
        problem=problem,
        raw_body=raw_body,
        method=method,
        url=url,
    )
    error_class = _STATUS_TO_ERROR.get(status_code)
    if error_class is None:
        error_class = InternalServerError if status_code >= 500 else APIError
    return error_class(message, fields)


def parse_problem(raw_body: str | None) -> Problem | None:
    """Parse an RFC 9457 body, returning ``None`` for anything that is not one.

    Deliberately forgiving in two directions:

    * A Cloudflare HTML interstitial or an empty body yields ``None`` — the
      caller still raises a typed :class:`APIError`, never a decode exception.
    * A body that IS shaped like a problem (string ``code`` + integer
      ``status``) but fails strict validation — because the server added a NEW
      problem code, which v1 allows — is still returned, with the unknown code
      degraded to a plain string rather than dropped.
    """
    if not raw_body:
        return None
    try:
        payload = json.loads(raw_body)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("code"), str) or not isinstance(payload.get("status"), int):
        return None
    try:
        return Problem.model_validate(payload)
    except ValidationError:
        return _lenient_problem(payload)


def _lenient_problem(payload: dict[str, Any]) -> Problem:
    """Build a :class:`Problem` from a problem-SHAPED body that failed validation.

    Constructed without validation so an unrecognized ``code`` survives, with
    every required field defaulted so attribute access can never blow up on a
    partial document. ``errors`` entries that do validate become real
    :class:`FieldError` objects; the rest are dropped rather than faked.
    """
    raw_errors = payload.get("errors")
    field_errors: list[FieldError] | None = None
    if isinstance(raw_errors, list):
        field_errors = []
        for entry in raw_errors:
            try:
                field_errors.append(FieldError.model_validate(entry))
            except ValidationError:
                continue

    code = payload.get("code")
    defaults: dict[str, Any] = {
        "type": payload.get("type") or "about:blank",
        "title": payload.get("title") or code,
        "status": payload.get("status"),
        "detail": payload.get("detail"),
        "code": code,
        "request_id": payload.get("request_id") or "",
    }
    merged: dict[str, Any] = {**payload, **defaults, "errors": field_errors}
    return Problem.model_construct(**merged)


def parse_retry_after_seconds(value: str | None) -> float | None:
    """RFC 9110 ``Retry-After``: delay-seconds or an HTTP-date."""
    if value is None:
        return None
    trimmed = value.strip()
    if re.fullmatch(r"\d+", trimmed):
        return float(trimmed)
    try:
        parsed = email.utils.parsedate_to_datetime(trimmed)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    return max(0.0, math.ceil(parsed.timestamp() - time.time()))


_MEMBER = re.compile(r'"(?P<name>[^"]+)"(?P<params>(?:\s*;\s*[a-z]+\s*=\s*[^,;]+)*)')


def _params(raw: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for chunk in raw.split(";"):
        if "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        try:
            out[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return out


def _int_header(headers: dict[str, str], name: str) -> int | None:
    raw = headers.get(name)
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def parse_rate_limit(headers: dict[str, str]) -> RateLimit:
    """Parse IETF draft-11 ``RateLimit-Policy`` / ``RateLimit`` + the ``X-`` trio.

    ``RateLimit-Policy: "api-calls-period";q=5000;w=2592000, "per-key-minute";q=120;w=60``
    ``RateLimit: "api-calls-period";r=4997;t=1814400``

    The obsolete split ``RateLimit-Limit``/``-Remaining``/``-Reset`` names are
    never read — the server does not emit them.
    """
    lowered = {key.lower(): value for key, value in headers.items()}

    policies: dict[str, dict[str, int]] = {}
    order: list[str] = []
    for match in _MEMBER.finditer(lowered.get("ratelimit-policy", "")):
        name = match.group("name")
        if name not in policies:
            order.append(name)
        policies[name] = _params(match.group("params"))

    state: dict[str, dict[str, int]] = {}
    for match in _MEMBER.finditer(lowered.get("ratelimit", "")):
        name = match.group("name")
        state[name] = _params(match.group("params"))
        if name not in policies:
            policies[name] = {}
            order.append(name)

    windows = tuple(
        RateLimitWindow(
            name=name,
            limit=policies.get(name, {}).get("q"),
            remaining=state.get(name, {}).get("r"),
            reset_seconds=state.get(name, {}).get("t"),
            window_seconds=policies.get(name, {}).get("w"),
        )
        for name in order
    )

    return RateLimit(
        windows=windows,
        limit=_int_header(lowered, "x-ratelimit-limit"),
        remaining=_int_header(lowered, "x-ratelimit-remaining"),
        reset=_int_header(lowered, "x-ratelimit-reset"),
    )
