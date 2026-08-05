"""Prod smoke that needs NO credentials — always runs, including on forks.

Two things are pinned here that no mock can pin:

1. The API's edge answers a default Python User-Agent with ``403 error code:
   1010``, before the request reaches the app. The SDK's own UA is what makes
   ``/v1`` reachable at all, so this is a standing regression guard, not a
   nicety.
2. An unauthenticated ``/v1`` call returns a real RFC 9457 problem document
   with ``code == "missing_credentials"`` and a ``request_id`` — the shape the
   whole error hierarchy is built on.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import httpx
import pytest

from getitdone_py import AuthenticationError, GetItDone, __version__

PROD_BASE_URL = "https://app.nowgetitdone.com"
PUBLIC_SPEC_URL = "https://nowgetitdone.com/docs/api/openapi.json"
SDK_USER_AGENT = f"getitdone-py/{__version__}"


@pytest.fixture(scope="module")
def unauthenticated_response() -> httpx.Response:
    return httpx.get(
        f"{PROD_BASE_URL}/v1/organizations",
        headers={"User-Agent": SDK_USER_AGENT, "Accept": "application/json"},
        timeout=30.0,
    )


def test_an_unauthenticated_call_returns_an_rfc_9457_problem_document(
    unauthenticated_response: httpx.Response,
):
    response = unauthenticated_response
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")

    problem = response.json()
    assert problem["code"] == "missing_credentials"
    assert problem["status"] == 401
    assert problem["request_id"]
    assert problem["type"].startswith("https://nowgetitdone.com/docs/api/problems/")


def test_the_x_request_id_header_is_present_on_an_error(
    unauthenticated_response: httpx.Response,
):
    assert unauthenticated_response.headers.get("x-request-id")


def test_the_default_python_user_agent_is_blocked_by_the_edge():
    """If this ever stops being true the SDK's mandatory UA can be revisited —
    until then, removing it breaks every request with a 403 that never reaches
    the application."""
    request = urllib.request.Request(f"{PROD_BASE_URL}/v1/organizations")  # noqa: S310
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(request, timeout=30)  # noqa: S310

    assert excinfo.value.code == 403, (
        "the edge no longer blocks default Python UAs — verify before relaxing anything"
    )


def test_the_sdk_reaches_the_api_with_an_invalid_key_and_raises_a_typed_error():
    with (
        GetItDone(api_key="gid_invalid_probe", base_url=PROD_BASE_URL, max_retries=0) as client,
        pytest.raises(AuthenticationError) as excinfo,
    ):
        client.organizations.list().page()

    error = excinfo.value
    assert error.status_code == 401
    assert error.code == "invalid_api_key"
    assert error.request_id
    assert error.request_id in str(error)


def test_the_public_openapi_document_is_reachable_and_matches_the_vendored_spec():
    """The nightly `spec-drift` job depends on this URL staying public."""
    from tests.helpers import load_spec

    response = httpx.get(
        PUBLIC_SPEC_URL,
        headers={"User-Agent": SDK_USER_AGENT, "Accept": "application/json"},
        timeout=60.0,
        follow_redirects=True,
    )
    assert response.status_code == 200

    live = json.loads(response.text)
    vendored = load_spec()

    live_operations = {
        operation["operationId"]
        for item in live["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    vendored_operations = {
        operation["operationId"]
        for item in vendored["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert live_operations == vendored_operations, (
        "the live spec and openapi/v1.json disagree — run scripts/sync-spec.sh "
        "and scripts/regenerate-models.sh"
    )
    assert len(live_operations) == 37
