"""Client construction, configuration and header assembly."""

from __future__ import annotations

import httpx
import pytest
import respx

from getitdone_py import (
    DEFAULT_BASE_URL,
    AsyncGetItDone,
    GetItDone,
    GetItDoneError,
    RequestOptions,
    __version__,
)

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def test_api_key_is_read_from_the_environment_when_not_passed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GETITDONE_API_KEY", "gid_from_env")
    with GetItDone() as client:
        assert client._core.api_key == "gid_from_env"


def test_explicit_api_key_beats_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GETITDONE_API_KEY", "gid_from_env")
    with GetItDone(api_key="gid_explicit") as client:
        assert client._core.api_key == "gid_explicit"


def test_missing_api_key_raises_an_actionable_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GETITDONE_API_KEY", raising=False)
    with pytest.raises(GetItDoneError) as excinfo:
        GetItDone()
    message = str(excinfo.value)
    assert "GETITDONE_API_KEY" in message
    assert "https://app.nowgetitdone.com/settings" in message


def test_base_url_defaults_to_production(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GETITDONE_BASE_URL", raising=False)
    with GetItDone(api_key="gid_x") as client:
        assert client.base_url == DEFAULT_BASE_URL == "https://app.nowgetitdone.com"


def test_base_url_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GETITDONE_BASE_URL", "https://staging.example.com")
    with GetItDone(api_key="gid_x") as client:
        assert client.base_url == "https://staging.example.com"


def test_trailing_slashes_are_stripped_from_the_base_url():
    with GetItDone(api_key="gid_x", base_url="https://example.com///") as client:
        assert client.base_url == "https://example.com"


def test_client_defaults_mirror_the_typescript_sdk():
    with GetItDone(api_key="gid_x") as client:
        assert client._core.timeout == 60.0
        assert client._core.max_retries == 2
        assert client._core.max_retry_after_seconds == 60.0


@respx.mock
def test_every_request_carries_bearer_auth_a_custom_user_agent_and_accept_json():
    route = respx.get("https://api.test/v1/usage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    with GetItDone(api_key="gid_secret", base_url="https://api.test") as client:
        client.request("GET", "/v1/usage")

    headers = route.calls[0].request.headers
    assert headers["authorization"] == "Bearer gid_secret"
    assert headers["user-agent"] == f"getitdone-sdk/{__version__}"
    assert headers["accept"] == "application/json"
    # /v1 is Bearer-ONLY: the legacy x-api-key scheme is never sent.
    assert "x-api-key" not in headers


@respx.mock
def test_a_default_python_user_agent_is_never_sent():
    """Cloudflare answers default Python UAs with `403 error code: 1010`."""
    route = respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url="https://api.test") as client:
        client.request("GET", "/v1/usage")

    user_agent = route.calls[0].request.headers["user-agent"]
    assert "python" not in user_agent.lower()
    assert "httpx" not in user_agent.lower()
    assert user_agent.startswith("getitdone-sdk/")


@respx.mock
def test_default_headers_are_merged_into_every_request():
    route = respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(
        api_key="gid_x", base_url="https://api.test", default_headers={"X-Trace": "abc"}
    ) as client:
        client.request("GET", "/v1/usage")

    assert route.calls[0].request.headers["x-trace"] == "abc"


@respx.mock
def test_per_request_headers_can_never_override_authorization():
    route = respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_real", base_url="https://api.test") as client:
        client.request(
            "GET",
            "/v1/usage",
            options=RequestOptions(headers={"Authorization": "Bearer gid_stale"}),
        )

    assert route.calls[0].request.headers["authorization"] == "Bearer gid_real"


@respx.mock
def test_default_headers_can_never_override_authorization():
    route = respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(
        api_key="gid_real",
        base_url="https://api.test",
        default_headers={"authorization": "Bearer gid_stale"},
    ) as client:
        client.request("GET", "/v1/usage")

    assert route.calls[0].request.headers["authorization"] == "Bearer gid_real"


@respx.mock
def test_content_type_json_is_only_sent_with_a_body():
    get_route = respx.get("https://api.test/v1/usage").mock(
        return_value=httpx.Response(200, json={})
    )
    post_route = respx.post("https://api.test/v1/tasks").mock(
        return_value=httpx.Response(200, json={})
    )
    with GetItDone(api_key="gid_x", base_url="https://api.test") as client:
        client.request("GET", "/v1/usage")
        client.request("POST", "/v1/tasks", body={"title": "t"})

    assert "content-type" not in get_route.calls[0].request.headers
    assert post_route.calls[0].request.headers["content-type"] == "application/json"


@respx.mock
def test_query_parameters_are_serialized_dropping_none_and_expanding_lists():
    route = respx.get("https://api.test/v1/tasks").mock(return_value=httpx.Response(200, json={}))
    with GetItDone(api_key="gid_x", base_url="https://api.test") as client:
        client.request(
            "GET",
            "/v1/tasks",
            query={"limit": 25, "after": None, "status": ["TODO", "DONE"], "archived": False},
        )

    url = route.calls[0].request.url
    assert "limit=25" in str(url)
    assert "after=" not in str(url)
    assert url.params.get_list("status") == ["TODO", "DONE"]
    assert "archived=false" in str(url)


@respx.mock
def test_a_204_response_yields_none_rather_than_a_decode_error():
    respx.delete("https://api.test/v1/api-keys/k1").mock(return_value=httpx.Response(204))
    with GetItDone(api_key="gid_x", base_url="https://api.test") as client:
        assert client.request("DELETE", "/v1/api-keys/k1") is None


@respx.mock
def test_an_injected_http_client_is_used_and_not_closed_by_the_sdk():
    respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    injected = httpx.Client()
    client = GetItDone(api_key="gid_x", base_url="https://api.test", http_client=injected)
    client.request("GET", "/v1/usage")
    client.close()
    assert not injected.is_closed
    injected.close()


@respx.mock
async def test_the_async_client_sends_the_same_headers():
    route = respx.get("https://api.test/v1/usage").mock(return_value=httpx.Response(200, json={}))
    async with AsyncGetItDone(api_key="gid_secret", base_url="https://api.test") as client:
        await client.request("GET", "/v1/usage")

    headers = route.calls[0].request.headers
    assert headers["authorization"] == "Bearer gid_secret"
    assert headers["user-agent"] == f"getitdone-sdk/{__version__}"


async def test_the_async_client_reads_the_same_env_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GETITDONE_API_KEY", "gid_env")
    monkeypatch.setenv("GETITDONE_BASE_URL", "https://staging.example.com/")
    async with AsyncGetItDone() as client:
        assert client._core.api_key == "gid_env"
        assert client.base_url == "https://staging.example.com"
