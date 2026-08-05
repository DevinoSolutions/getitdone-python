"""RFC 9457 problem parsing and the typed exception hierarchy."""

from __future__ import annotations

import httpx
import pytest
import respx

from getitdone_py import (
    PROBLEM_CODES,
    APIError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    GetItDone,
    GetItDoneError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from getitdone_py.errors import parse_problem, parse_retry_after_seconds
from tests.helpers import load_fixture, load_spec

BASE = "https://api.test"

CODE_TO_EXPECTED = {
    "missing_credentials": (401, AuthenticationError),
    "invalid_api_key": (401, AuthenticationError),
    "invalid_token": (401, AuthenticationError),
    "insufficient_scope": (403, PermissionDeniedError),
    "feature_not_enabled": (403, PermissionDeniedError),
    "validation_failed": (400, BadRequestError),
    "resource_not_found": (404, NotFoundError),
    "rate_limited": (429, RateLimitError),
    "quota_exhausted": (429, RateLimitError),
    "idempotency_key_missing": (400, BadRequestError),
    "idempotency_key_reused": (422, UnprocessableEntityError),
    "idempotency_in_progress": (409, ConflictError),
    "webhook_url_rejected": (422, UnprocessableEntityError),
    "delivery_already_pending": (409, ConflictError),
    "internal_error": (500, InternalServerError),
}


def problem_body(code: str, status: int, **extra: object) -> dict[str, object]:
    return {
        "type": f"https://nowgetitdone.com/docs/api/problems/{code.replace('_', '-')}",
        "title": code.replace("_", " ").capitalize(),
        "status": status,
        "code": code,
        "request_id": "req_abc123",
        **extra,
    }


def test_the_sdk_code_vocabulary_matches_the_specs_problem_codes():
    spec = load_spec()
    spec_codes = set(spec["components"]["schemas"]["Problem"]["properties"]["code"]["enum"])
    assert set(PROBLEM_CODES) == spec_codes
    assert len(PROBLEM_CODES) == 15


@pytest.mark.parametrize("code", sorted(CODE_TO_EXPECTED))
@respx.mock
def test_each_problem_code_raises_its_mapped_exception_class(code: str):
    status, expected = CODE_TO_EXPECTED[code]
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            status,
            json=problem_body(code, status),
            headers={"content-type": "application/problem+json", "x-request-id": "req_abc123"},
        )
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(expected) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    error = excinfo.value
    assert isinstance(error, APIError)
    assert isinstance(error, GetItDoneError)
    assert error.code == code
    assert error.status_code == status
    assert error.request_id == "req_abc123"
    assert error.problem is not None


@respx.mock
def test_the_request_id_appears_in_the_exception_message():
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            404,
            json=problem_body("resource_not_found", 404, detail="Task T-9 not found."),
            headers={"x-request-id": "req_abc123"},
        )
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(NotFoundError) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    message = str(excinfo.value)
    assert "req_abc123" in message
    assert "resource_not_found" in message
    assert "Task T-9 not found." in message


@respx.mock
def test_validation_failures_expose_field_errors():
    respx.post(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            400,
            json=problem_body(
                "validation_failed",
                400,
                detail="Request validation failed.",
                errors=[
                    {"pointer": "/title", "code": "too_small", "message": "String too short"},
                    {"pointer": "/priority", "code": "invalid_enum", "message": "Invalid option"},
                ],
            ),
        )
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(BadRequestError) as excinfo,
    ):
        client.request("POST", "/v1/tasks", body={"title": ""})

    field_errors = excinfo.value.field_errors
    assert [error.pointer for error in field_errors] == ["/title", "/priority"]
    assert field_errors[0].code == "too_small"


@respx.mock
def test_a_cloudflare_html_body_still_raises_a_typed_error_not_a_decode_crash():
    html = "<html><head><title>Access denied</title></head><body>error code: 1010</body></html>"
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(403, text=html, headers={"content-type": "text/html"})
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(PermissionDeniedError) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    error = excinfo.value
    assert error.problem is None
    assert error.code is None
    assert error.raw_body is not None
    assert "error code: 1010" in error.raw_body
    assert "error code: 1010" in str(error)


@respx.mock
def test_an_empty_error_body_still_raises_a_typed_error():
    respx.get(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(404, text=""))
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(NotFoundError) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    assert excinfo.value.problem is None
    assert "no response body" in str(excinfo.value)


@respx.mock
def test_an_unmapped_4xx_status_raises_the_base_api_error():
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(418, json=problem_body("internal_error", 418))
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(APIError) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    assert type(excinfo.value) is APIError


@respx.mock
def test_quota_exhausted_is_distinguishable_from_a_burst_rate_limit():
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(429, json=problem_body("quota_exhausted", 429))
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client,
        pytest.raises(RateLimitError) as excinfo,
    ):
        client.request("GET", "/v1/tasks")

    assert excinfo.value.is_quota_exhausted is True


def test_a_new_server_side_problem_code_degrades_to_a_string_instead_of_being_dropped():
    """v1 may add codes additively; an older SDK must not lose the document."""
    problem = parse_problem(
        '{"type":"https://x/y","title":"New","status":400,'
        '"code":"brand_new_code","request_id":"req_1"}'
    )
    assert problem is not None
    assert problem.code == "brand_new_code"
    assert problem.request_id == "req_1"


def test_a_real_production_problem_document_parses():
    problem = parse_problem(
        httpx.Response(401, json=load_fixture("problem_missing_credentials")).text
    )
    assert problem is not None
    assert problem.code == "missing_credentials"


@pytest.mark.parametrize(
    "body",
    ["", None, "not json at all", "[1,2,3]", '{"hello":"world"}', '{"code":1,"status":"x"}'],
)
def test_non_problem_bodies_parse_to_none(body: str | None):
    assert parse_problem(body) is None


def test_retry_after_accepts_delay_seconds_and_http_dates():
    assert parse_retry_after_seconds("30") == 30
    assert parse_retry_after_seconds("  12 ") == 12
    assert parse_retry_after_seconds(None) is None
    assert parse_retry_after_seconds("not-a-date") is None

    far_future = parse_retry_after_seconds("Wed, 01 Jan 2098 00:00:00 GMT")
    assert far_future is not None and far_future > 0
    # A date in the past clamps to zero rather than going negative.
    assert parse_retry_after_seconds("Wed, 21 Oct 2015 07:28:00 GMT") == 0


@respx.mock
async def test_the_async_client_raises_the_same_typed_errors():
    from getitdone_py import AsyncGetItDone

    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(403, json=problem_body("feature_not_enabled", 403))
    )
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE, max_retries=0) as client:
        with pytest.raises(PermissionDeniedError) as excinfo:
            await client.request("GET", "/v1/tasks")

    assert excinfo.value.code == "feature_not_enabled"
