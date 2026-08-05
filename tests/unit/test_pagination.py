"""Cursor pagination: auto-iteration, the page escape hatch, and query fidelity.

The server REJECTS a cursor reused with different query params
(`packages/api-contracts/src/pagination.ts`), so the SDK must re-send the
original query verbatim and only swap `after`.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from getitdone_py import AsyncGetItDone, GetItDone
from getitdone_py._pagination import AsyncPage, AsyncPaginator, Page, Paginator

BASE = "https://api.test"


def envelope(ids: list[str], next_cursor: str | None) -> dict[str, object]:
    return {
        "data": [{"id": task_id} for task_id in ids],
        "has_more": next_cursor is not None,
        "next_cursor": next_cursor,
    }


def three_pages() -> list[httpx.Response]:
    return [
        httpx.Response(200, json=envelope(["T-1", "T-2"], "cur_1")),
        httpx.Response(200, json=envelope(["T-3", "T-4"], "cur_2")),
        httpx.Response(200, json=envelope(["T-5"], None)),
    ]


@respx.mock
def test_iterating_a_list_walks_every_page():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        ids = [task["id"] for task in client.tasks.list({"limit": 2})]

    assert ids == ["T-1", "T-2", "T-3", "T-4", "T-5"]
    assert route.call_count == 3


@respx.mock
def test_the_original_query_is_resent_verbatim_with_only_the_cursor_added():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        list(client.tasks.list({"limit": 2, "status": "TODO", "project_id": "p_1"}))

    first, second, third = (call.request.url.params for call in route.call_count and route.calls)
    assert "after" not in first
    for params in (second, third):
        assert params["limit"] == "2"
        assert params["status"] == "TODO"
        assert params["project_id"] == "p_1"
    assert second["after"] == "cur_1"
    assert third["after"] == "cur_2"


@respx.mock
def test_has_more_false_terminates_the_walk():
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(200, json=envelope(["T-1"], None))
    )
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        assert len(list(client.tasks.list())) == 1
    assert route.call_count == 1


@respx.mock
def test_a_null_next_cursor_terminates_even_when_has_more_is_true():
    """Defensive: never loop forever on an inconsistent envelope."""
    route = respx.get(f"{BASE}/v1/tasks").mock(
        return_value=httpx.Response(
            200, json={"data": [{"id": "T-1"}], "has_more": True, "next_cursor": None}
        )
    )
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        assert len(list(client.tasks.list())) == 1
    assert route.call_count == 1


@respx.mock
def test_an_empty_first_page_yields_nothing():
    respx.get(f"{BASE}/v1/tasks").mock(return_value=httpx.Response(200, json=envelope([], None)))
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        assert list(client.tasks.list()) == []


@respx.mock
def test_the_page_escape_hatch_exposes_the_raw_envelope():
    respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        page = client.tasks.list({"limit": 2}).page()

        assert isinstance(page, Page)
        assert [task["id"] for task in page.data] == ["T-1", "T-2"]
        assert page.has_more is True
        assert page.next_cursor == "cur_1"
        assert len(page) == 2

        second = page.get_next_page()
        assert second is not None
        assert [task["id"] for task in second.data] == ["T-3", "T-4"]

        third = second.get_next_page()
        assert third is not None
        assert third.has_more is False
        assert third.get_next_page() is None


@respx.mock
def test_a_list_method_returns_a_lazy_paginator_that_has_not_called_the_api_yet():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        paginator = client.tasks.list()
        assert isinstance(paginator, Paginator)
        assert route.call_count == 0
        paginator.page()
        assert route.call_count == 1


@pytest.mark.parametrize(
    ("accessor", "args", "path"),
    [
        ("organizations.list", (), "/v1/organizations"),
        ("members.list", (), "/v1/members"),
        ("projects.list", (), "/v1/projects"),
        ("api_keys.list", (), "/v1/api-keys"),
        ("tasks.list", (), "/v1/tasks"),
        ("tasks.list_history", ("T-1",), "/v1/tasks/T-1/history"),
        ("attachments.list", ("T-1",), "/v1/tasks/T-1/attachments"),
        ("webhook_endpoints.list", (), "/v1/webhook-endpoints"),
        ("webhook_endpoints.list_deliveries", ("we_1",), "/v1/webhook-endpoints/we_1/deliveries"),
    ],
)
@respx.mock
def test_all_nine_paginated_lists_auto_iterate(accessor: str, args: tuple, path: str):
    route = respx.get(f"{BASE}{path}").mock(
        side_effect=[
            httpx.Response(200, json=envelope(["a"], "cur_1")),
            httpx.Response(200, json=envelope(["b"], None)),
        ]
    )
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        target = client
        for part in accessor.split("."):
            target = getattr(target, part)
        items = list(target(*args))

    assert [item["id"] for item in items] == ["a", "b"]
    assert route.call_count == 2


@respx.mock
async def test_the_async_twin_walks_every_page():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as client:
        ids = [task["id"] async for task in client.tasks.list({"limit": 2})]

    assert ids == ["T-1", "T-2", "T-3", "T-4", "T-5"]
    assert route.call_count == 3


@respx.mock
async def test_the_async_page_escape_hatch_works():
    respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as client:
        paginator = client.tasks.list()
        assert isinstance(paginator, AsyncPaginator)

        page = await paginator.page()
        assert isinstance(page, AsyncPage)
        assert page.next_cursor == "cur_1"

        second = await page.get_next_page()
        assert second is not None
        assert [task["id"] for task in second.data] == ["T-3", "T-4"]


@respx.mock
async def test_the_async_walk_resends_the_original_query():
    route = respx.get(f"{BASE}/v1/tasks").mock(side_effect=three_pages())
    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as client:
        _ = [task async for task in client.tasks.list({"limit": 2, "status": "TODO"})]

    last = route.calls[-1].request.url.params
    assert last["limit"] == "2"
    assert last["status"] == "TODO"
    assert last["after"] == "cur_2"
