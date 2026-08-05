"""The retry contract, ported from `packages/sdk/src/core/http.ts`."""

from __future__ import annotations

import random

import httpx
import pytest
import respx

from getitdone_py import (
    APIConnectionError,
    APIConnectionTimeoutError,
    APIError,
    AsyncGetItDone,
    ConflictError,
    GetItDone,
    InternalServerError,
    RateLimitError,
    RequestOptions,
)
from getitdone_py._http import backoff_seconds, is_retryable_status

BASE = "https://api.test"


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record backoff sleeps instead of serving them."""
    slept: list[float] = []

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    async def fake_async_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("getitdone_py._http.time.sleep", fake_sleep)
    monkeypatch.setattr("getitdone_py._http.asyncio.sleep", fake_async_sleep)
    return slept


def client(**kwargs: object) -> GetItDone:
    return GetItDone(api_key="gid_x", base_url=BASE, **kwargs)  # type: ignore[arg-type]


def problem(code: str, status: int) -> dict[str, object]:
    return {
        "type": "https://x/y",
        "title": code,
        "status": status,
        "code": code,
        "request_id": "req_1",
    }


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
@respx.mock
def test_retryable_statuses_are_retried_then_succeed(status: int):
    route = respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(status, json=problem("internal_error", status)),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with client() as sdk:
        assert sdk.request("GET", "/v1/tasks") == {"ok": True}
    assert route.call_count == 2


@respx.mock
def test_the_retry_budget_is_exhausted_and_the_last_error_is_raised():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(500, json=problem("internal_error", 500))
    )
    with client(max_retries=2) as sdk, pytest.raises(InternalServerError):
        sdk.request("GET", "/v1/tasks")
    assert route.call_count == 3  # first attempt + 2 retries


@respx.mock
def test_max_retries_zero_makes_exactly_one_attempt():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(503, json=problem("internal_error", 503))
    )
    with client(max_retries=0) as sdk, pytest.raises(InternalServerError):
        sdk.request("GET", "/v1/tasks")
    assert route.call_count == 1


@respx.mock
def test_per_request_max_retries_overrides_the_client_default():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(500, json=problem("internal_error", 500))
    )
    with client(max_retries=5) as sdk, pytest.raises(InternalServerError):
        sdk.request("GET", "/v1/tasks", options=RequestOptions(max_retries=1))
    assert route.call_count == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
@respx.mock
def test_non_retryable_statuses_fail_on_the_first_attempt(status: int):
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(status, json=problem("validation_failed", status))
    )
    with client() as sdk, pytest.raises(APIError):
        sdk.request("GET", "/v1/tasks")
    assert route.call_count == 1


@respx.mock
def test_a_post_without_an_idempotency_key_is_never_retried():
    route = respx.post(f"{BASE}/v1/webhook-endpoints/e1/verify").mock(
        return_value=httpx.Response(500, json=problem("internal_error", 500))
    )
    with client() as sdk, pytest.raises(InternalServerError):
        sdk.request("POST", "/v1/webhook-endpoints/e1/verify")
    assert route.call_count == 1


@respx.mock
def test_a_post_with_an_idempotency_key_is_retried():
    route = respx.post(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(500, json=problem("internal_error", 500)),
            httpx.Response(200, json={"id": "T-1"}),
        ]
    )
    with client() as sdk:
        sdk.request("POST", "/v1/tasks", body={"title": "x"}, idempotent=True)
    assert route.call_count == 2


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@respx.mock
def test_get_patch_and_delete_are_retry_eligible_without_a_key(method: str):
    route = respx.request(method, f"{BASE}/v1/tasks/T-1").mock(
        side_effect=[
            httpx.Response(500, json=problem("internal_error", 500)),
            httpx.Response(200, json={"id": "T-1"}),
        ]
    )
    with client() as sdk:
        sdk.request(method, "/v1/tasks/T-1")
    assert route.call_count == 2


@respx.mock
def test_409_is_retried_only_when_an_idempotency_key_was_sent():
    idempotent_route = respx.post(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(409, json=problem("idempotency_in_progress", 409)),
            httpx.Response(200, json={"id": "T-1"}),
        ]
    )
    with client() as sdk:
        sdk.request("POST", "/v1/tasks", body={"title": "x"}, idempotent=True)
    assert idempotent_route.call_count == 2

    plain_route = respx.post(f"{BASE}/v1/webhook-endpoints/e1/deliveries/d1/replay").mock(
        return_value=httpx.Response(409, json=problem("delivery_already_pending", 409))
    )
    with client() as sdk, pytest.raises(ConflictError):
        sdk.request("POST", "/v1/webhook-endpoints/e1/deliveries/d1/replay")
    assert plain_route.call_count == 1


@respx.mock
def test_409_on_a_get_is_not_retried_without_a_key():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(409, json=problem("idempotency_in_progress", 409))
    )
    with client() as sdk, pytest.raises(ConflictError):
        sdk.request("GET", "/v1/tasks")
    assert route.call_count == 1


@respx.mock
def test_transport_errors_are_retried_then_raise_api_connection_error():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=httpx.ConnectError("boom"))
    with client(max_retries=2) as sdk, pytest.raises(APIConnectionError) as excinfo:
        sdk.request("GET", "/v1/tasks")
    assert route.call_count == 3
    assert isinstance(excinfo.value.__cause__, httpx.ConnectError)


@respx.mock
def test_a_transport_error_recovers_on_a_retry():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json={"ok": True})]
    )
    with client() as sdk:
        assert sdk.request("GET", "/v1/tasks") == {"ok": True}
    assert route.call_count == 2


@respx.mock
def test_a_timeout_raises_the_timeout_subclass():
    respx.get(f"{BASE}/v1/tasks").mock(side_effect=httpx.ReadTimeout("slow"))
    with client(max_retries=0) as sdk, pytest.raises(APIConnectionTimeoutError):
        sdk.request("GET", "/v1/tasks")


@respx.mock
def test_a_post_without_a_key_is_not_retried_on_a_transport_error():
    route = respx.post(f"{BASE}/v1/webhook-endpoints/e1/verify").mock(
        side_effect=httpx.ConnectError("boom")
    )
    with client() as sdk, pytest.raises(APIConnectionError):
        sdk.request("POST", "/v1/webhook-endpoints/e1/verify")
    assert route.call_count == 1


@respx.mock
def test_retry_after_in_seconds_is_honored_instead_of_the_backoff(
    _no_real_sleeping: list[float],
):
    respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(429, json=problem("rate_limited", 429), headers={"retry-after": "7"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with client() as sdk:
        sdk.request("GET", "/v1/tasks")
    assert _no_real_sleeping == [7.0]


@respx.mock
def test_retry_after_as_an_http_date_is_honored(_no_real_sleeping: list[float]):
    respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(
                503,
                json=problem("internal_error", 503),
                headers={"retry-after": "Wed, 21 Oct 2015 07:28:00 GMT"},
            ),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with client() as sdk:
        sdk.request("GET", "/v1/tasks")
    # A past date clamps to 0 seconds — retried immediately, never negative.
    assert _no_real_sleeping == [0.0]


@respx.mock
def test_a_retry_after_above_the_ceiling_aborts_instead_of_sleeping(
    _no_real_sleeping: list[float],
):
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            429, json=problem("quota_exhausted", 429), headers={"retry-after": "3600"}
        )
    )
    with client(max_retry_after_seconds=60.0) as sdk, pytest.raises(RateLimitError) as excinfo:
        sdk.request("GET", "/v1/tasks")

    assert route.call_count == 1
    assert _no_real_sleeping == []
    assert excinfo.value.retry_after == 3600


@respx.mock
def test_a_raised_retry_after_ceiling_allows_the_wait(_no_real_sleeping: list[float]):
    respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(429, json=problem("rate_limited", 429), headers={"retry-after": "120"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    with client(max_retry_after_seconds=300.0) as sdk:
        sdk.request("GET", "/v1/tasks")
    assert _no_real_sleeping == [120.0]


@pytest.mark.parametrize("attempt", [0, 1, 2, 3, 4, 5])
def test_backoff_stays_within_the_jittered_bounds(attempt: int):
    base = min(8.0, 0.5 * 2**attempt)
    rng = random.Random(1234)
    for _ in range(200):
        delay = backoff_seconds(attempt, rng)
        assert base * 0.75 <= delay <= base * 1.25
    assert backoff_seconds(attempt, _FixedRandom(0.0)) == pytest.approx(base * 0.75)
    assert backoff_seconds(attempt, _FixedRandom(1.0)) == pytest.approx(base * 1.25)


def test_backoff_is_capped_at_eight_seconds():
    assert backoff_seconds(100, _FixedRandom(1.0)) == pytest.approx(10.0)  # 8s * 1.25 jitter
    assert backoff_seconds(100, _FixedRandom(0.0)) == pytest.approx(6.0)


class _FixedRandom(random.Random):
    def __init__(self, value: float):
        super().__init__()
        self._value = value

    def random(self) -> float:  # type: ignore[override]
        return self._value


def test_is_retryable_status_matches_the_typescript_predicate():
    for status in (408, 429, 500, 502, 503, 504, 599):
        assert is_retryable_status(status, False) is True
    for status in (400, 401, 403, 404, 422):
        assert is_retryable_status(status, False) is False
    assert is_retryable_status(409, False) is False
    assert is_retryable_status(409, True) is True


@respx.mock
async def test_the_async_client_retries_with_the_same_contract(_no_real_sleeping: list[float]):
    route = respx.get(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(500, json=problem("internal_error", 500)),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as sdk:
        assert await sdk.request("GET", "/v1/tasks") == {"ok": True}
    assert route.call_count == 2
    assert len(_no_real_sleeping) == 1


@respx.mock
async def test_the_async_client_never_retries_a_keyless_post():
    route = respx.post(f"{BASE}/v1/webhook-endpoints/e1/verify").mock(
        return_value=httpx.Response(500, json=problem("internal_error", 500))
    )
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as sdk:
        with pytest.raises(InternalServerError):
            await sdk.request("POST", "/v1/webhook-endpoints/e1/verify")
    assert route.call_count == 1
