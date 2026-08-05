"""Idempotency-Key semantics on the 10 declared-idempotent POSTs."""

from __future__ import annotations

import httpx
import pytest
import respx

from getitdone_py import AsyncGetItDone, GetItDone, InternalServerError, RequestOptions
from tests.helpers import spec_operations

BASE = "https://api.test"

#: The 10 POSTs the /v1 registry declares idempotent (x-idempotent: true).
IDEMPOTENT_OPERATIONS = [
    ("POST", "/v1/projects"),
    ("POST", "/v1/api-keys"),
    ("POST", "/v1/tasks"),
    ("POST", "/v1/tasks/T-1/archive"),
    ("POST", "/v1/tasks/T-1/unarchive"),
    ("POST", "/v1/daily-plan/entries"),
    ("POST", "/v1/tasks/T-1/attachments/uploads"),
    ("POST", "/v1/tasks/T-1/attachments"),
    ("POST", "/v1/webhook-endpoints"),
    ("POST", "/v1/webhook-endpoints/e1/rotate-secret"),
]

#: POSTs that are deliberately NOT idempotent — re-runnable probes and replays.
NON_IDEMPOTENT_POSTS = [
    "/v1/webhook-endpoints/e1/verify",
    "/v1/webhook-endpoints/e1/test-event",
    "/v1/webhook-endpoints/e1/deliveries/d1/replay",
    "/v1/webhook-endpoints/e1/replay-failed",
]


def test_the_spec_declares_exactly_ten_idempotent_operations():
    idempotent = {op for op, (_, _, idem, _) in spec_operations().items() if idem}
    assert idempotent == {
        "createProject",
        "createApiKey",
        "createTask",
        "archiveTask",
        "unarchiveTask",
        "createDailyPlanEntry",
        "createAttachmentUpload",
        "createTaskAttachment",
        "createWebhookEndpoint",
        "rotateWebhookEndpointSecret",
    }
    assert len(idempotent) == 10


@pytest.mark.parametrize(("method", "path"), IDEMPOTENT_OPERATIONS)
@respx.mock
def test_a_key_is_auto_generated_on_every_declared_idempotent_post(method: str, path: str):
    route = respx.post(f"{BASE}{path}").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request(method, path, body={}, idempotent=True)

    key = route.calls[0].request.headers.get("idempotency-key")
    assert key is not None
    assert key.startswith("gid-sdk-")
    assert len(key) > len("gid-sdk-")


@pytest.mark.parametrize("path", NON_IDEMPOTENT_POSTS)
@respx.mock
def test_no_key_is_sent_on_the_non_idempotent_posts(path: str):
    route = respx.post(f"{BASE}{path}").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request("POST", path, body={})

    assert "idempotency-key" not in route.calls[0].request.headers


@pytest.mark.parametrize(("method", "path"), [("GET", "/v1/tasks"), ("PATCH", "/v1/tasks/T-1")])
@respx.mock
def test_no_key_is_sent_on_reads_and_patches(method: str, path: str):
    route = respx.request(method, f"{BASE}{path}").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request(method, path)

    assert "idempotency-key" not in route.calls[0].request.headers


@respx.mock
def test_no_key_is_sent_on_delete():
    route = respx.delete(f"{BASE}/v1/api-keys/k1").mock(return_value=httpx.Response(204))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request("DELETE", "/v1/api-keys/k1")

    assert "idempotency-key" not in route.calls[0].request.headers


@respx.mock
def test_the_same_key_is_replayed_across_every_retry_of_one_logical_call(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("getitdone_py._http.time.sleep", lambda _seconds: None)
    route = respx.post(f"{BASE}/v1/tasks").mock(
        side_effect=[
            httpx.Response(500, json={"code": "internal_error", "status": 500}),
            httpx.Response(409, json={"code": "idempotency_in_progress", "status": 409}),
            httpx.Response(200, json={"id": "T-1"}),
        ]
    )
    with GetItDone(api_key="gid_x", base_url=BASE, max_retries=2) as client:
        client.request("POST", "/v1/tasks", body={"title": "x"}, idempotent=True)

    keys = {call.request.headers["idempotency-key"] for call in route.calls}
    assert route.call_count == 3
    assert len(keys) == 1, "a retry must REPLAY, so it must present the same key"


@respx.mock
def test_two_separate_calls_get_two_different_keys():
    route = respx.post(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request("POST", "/v1/tasks", body={"title": "a"}, idempotent=True)
        client.request("POST", "/v1/tasks", body={"title": "b"}, idempotent=True)

    keys = {call.request.headers["idempotency-key"] for call in route.calls}
    assert len(keys) == 2


@respx.mock
def test_a_caller_supplied_key_wins_over_auto_generation():
    route = respx.post(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.request(
            "POST",
            "/v1/tasks",
            body={"title": "x"},
            idempotent=True,
            options=RequestOptions(idempotency_key="order-4711"),
        )

    assert route.calls[0].request.headers["idempotency-key"] == "order-4711"


@respx.mock
def test_a_caller_supplied_key_makes_even_a_non_declared_post_retryable():
    route = respx.post(f"{BASE}/v1/webhook-endpoints/e1/verify").mock(
        return_value=httpx.Response(500, json={"code": "internal_error", "status": 500})
    )
    with (
        GetItDone(api_key="gid_x", base_url=BASE, max_retries=1) as client,
        pytest.raises(InternalServerError),
    ):
        client.request(
            "POST",
            "/v1/webhook-endpoints/e1/verify",
            options=RequestOptions(idempotency_key="probe-1"),
        )
    assert route.call_count == 2


@respx.mock
def test_the_idempotency_replayed_response_header_is_exposed():
    respx.post(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            200, json={"id": "T-1"}, headers={"idempotency-replayed": "true"}
        )
    )
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        result = client._core.request_with_response(
            _params("POST", "/v1/tasks", body={"title": "x"})
        )

    assert result.replayed is True
    assert result.data == {"id": "T-1"}


@respx.mock
def test_a_fresh_execution_is_not_marked_replayed():
    respx.post(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(200, json={"id": "T-1"}))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        result = client._core.request_with_response(
            _params("POST", "/v1/tasks", body={"title": "x"})
        )

    assert result.replayed is False


def _params(method: str, path: str, body: object = None):
    from getitdone_py._http import RequestParams

    return RequestParams(method=method, path=path, body=body, idempotent=True)  # type: ignore[arg-type]


@respx.mock
async def test_the_async_client_auto_generates_a_key_too():
    route = respx.post(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(200, json={}))
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as client:
        await client.request("POST", "/v1/tasks", body={"title": "x"}, idempotent=True)

    assert route.calls[0].request.headers["idempotency-key"].startswith("gid-sdk-")
