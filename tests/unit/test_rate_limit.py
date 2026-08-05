"""IETF draft-11 rate-limit header parsing.

Producer: `apps/web/src/lib/public-api/rate-limit-headers.ts`. The obsolete
split `RateLimit-Limit` / `-Remaining` / `-Reset` names are never emitted and
never read.
"""

from __future__ import annotations

import httpx
import respx

from getitdone_py import GetItDone, RateLimitError
from getitdone_py.errors import parse_rate_limit

BASE = "https://api.test"

SINGLE_WINDOW = {
    "RateLimit-Policy": '"api-calls-period";q=5000;w=2592000',
    "RateLimit": '"api-calls-period";r=4997;t=1814400',
    "X-RateLimit-Limit": "5000",
    "X-RateLimit-Remaining": "4997",
    "X-RateLimit-Reset": "1785000000",
}

MULTI_WINDOW = {
    "RateLimit-Policy": '"per-key-minute";q=120;w=60, "api-calls-period";q=5000;w=2592000',
    "RateLimit": '"per-key-minute";r=118;t=42',
    "X-RateLimit-Limit": "120",
    "X-RateLimit-Remaining": "118",
    "X-RateLimit-Reset": "1785000042",
}


def test_a_single_window_policy_parses():
    rate_limit = parse_rate_limit(SINGLE_WINDOW)
    assert len(rate_limit.windows) == 1

    window = rate_limit.windows[0]
    assert window.name == "api-calls-period"
    assert window.limit == 5000
    assert window.remaining == 4997
    assert window.reset_seconds == 1814400
    assert window.window_seconds == 2592000

    assert rate_limit.limit == 5000
    assert rate_limit.remaining == 4997
    assert rate_limit.reset == 1785000000


def test_the_multi_window_policy_keeps_order_and_marks_the_primary():
    rate_limit = parse_rate_limit(MULTI_WINDOW)
    assert [w.name for w in rate_limit.windows] == ["per-key-minute", "api-calls-period"]

    primary = rate_limit.primary
    assert primary is not None
    assert primary.name == "per-key-minute"
    assert primary.limit == 120
    assert primary.remaining == 118
    assert primary.reset_seconds == 42

    # The burst window carries state; the period window carries policy only.
    period = rate_limit.windows[1]
    assert period.limit == 5000
    assert period.window_seconds == 2592000
    assert period.remaining is None


def test_header_names_are_matched_case_insensitively():
    rate_limit = parse_rate_limit(
        {
            "ratelimit-policy": '"burst";q=10;w=1',
            "RATELIMIT": '"burst";r=9;t=1',
            "x-ratelimit-limit": "10",
        }
    )
    assert rate_limit.windows[0].name == "burst"
    assert rate_limit.windows[0].remaining == 9
    assert rate_limit.limit == 10


def test_missing_headers_parse_to_an_empty_rate_limit():
    rate_limit = parse_rate_limit({})
    assert rate_limit.windows == ()
    assert rate_limit.primary is None
    assert rate_limit.limit is None
    assert rate_limit.remaining is None
    assert rate_limit.reset is None


def test_malformed_values_are_ignored_rather_than_raising():
    rate_limit = parse_rate_limit(
        {
            "RateLimit-Policy": '"weird";q=notanumber;w=60',
            "RateLimit": "garbage without quotes",
            "X-RateLimit-Limit": "nope",
        }
    )
    assert rate_limit.windows[0].name == "weird"
    assert rate_limit.windows[0].limit is None
    assert rate_limit.windows[0].window_seconds == 60
    assert rate_limit.limit is None


def test_the_obsolete_split_header_names_are_not_read():
    rate_limit = parse_rate_limit(
        {"RateLimit-Limit": "999", "RateLimit-Remaining": "9", "RateLimit-Reset": "60"}
    )
    assert rate_limit.windows == ()
    assert rate_limit.limit is None


def test_a_window_named_only_in_the_state_header_still_appears():
    rate_limit = parse_rate_limit({"RateLimit": '"surprise";r=3;t=10'})
    assert rate_limit.windows[0].name == "surprise"
    assert rate_limit.windows[0].remaining == 3
    assert rate_limit.windows[0].limit is None


@respx.mock
def test_a_429_exposes_the_parsed_rate_limit_and_retry_after():
    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            429,
            json={
                "type": "https://x/y",
                "title": "Rate limited",
                "status": 429,
                "code": "rate_limited",
                "request_id": "req_1",
            },
            headers={**MULTI_WINDOW, "retry-after": "42"},
        )
    )
    with GetItDone(api_key="gid_x", base_url=BASE, max_retry_after_seconds=1.0) as client:
        try:
            client.request("GET", "/v1/tasks")
            raise AssertionError("expected RateLimitError")
        except RateLimitError as error:
            assert error.retry_after == 42
            assert error.is_quota_exhausted is False
            primary = error.rate_limit.primary
            assert primary is not None
            assert primary.name == "per-key-minute"
            assert primary.remaining == 118


@respx.mock
def test_rate_limit_headers_are_available_on_successful_responses():
    from getitdone_py._http import RequestParams

    respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(200, json={"data": []}, headers=SINGLE_WINDOW)
    )
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        response = client._core.request_with_response(RequestParams(method="GET", path="/v1/tasks"))

    rate_limit = parse_rate_limit(response.headers)
    assert rate_limit.limit == 5000
    assert rate_limit.windows[0].name == "api-calls-period"
