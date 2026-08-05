"""Every one of the 37 methods must build the right method + path + query + body.

Each case is checked against the vendored spec: the recorded request path is
matched back to its OpenAPI path template, and that template must belong to the
operation the method claims to implement. A method pointed at the wrong route
therefore cannot pass.
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

import httpx
import pytest
import respx

from getitdone_py import AsyncGetItDone, GetItDone
from getitdone_py._pagination import AsyncPaginator, Paginator
from tests.helpers import spec_operations
from tests.unit.test_operation_coverage import OPERATION_MAP, resolve

BASE = "https://api.test"


class Case(NamedTuple):
    operation_id: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    expected_path: str
    expected_query: dict[str, list[str]] = {}
    expected_body: Any = None


TASK_BODY = {"title": "Ship it"}
ENTRY_BODY = {"section": "PROGRESS"}

CASES: list[Case] = [
    Case("listOrganizations", (), {}, "/v1/organizations"),
    Case("getOrganization", ("org_1",), {}, "/v1/organizations/org_1"),
    Case("getUsage", (), {}, "/v1/usage"),
    Case("listMembers", ({"limit": 50},), {}, "/v1/members", {"limit": ["50"]}),
    Case("listProjects", ({"limit": 2},), {}, "/v1/projects", {"limit": ["2"]}),
    Case("getProject", ("p_1",), {}, "/v1/projects/p_1"),
    Case("createProject", ({"name": "Website"},), {}, "/v1/projects", {}, {"name": "Website"}),
    Case("listApiKeys", (), {}, "/v1/api-keys"),
    Case(
        "createApiKey",
        ({"name": "ci", "scopes": ["tasks:read"]},),
        {},
        "/v1/api-keys",
        {},
        {"name": "ci", "scopes": ["tasks:read"]},
    ),
    Case("deleteApiKey", ("key_1",), {}, "/v1/api-keys/key_1"),
    Case("listTasks", ({"status": "TODO"},), {}, "/v1/tasks", {"status": ["TODO"]}),
    Case("getTask", ("T-42",), {}, "/v1/tasks/T-42"),
    Case("createTask", (TASK_BODY,), {}, "/v1/tasks", {}, TASK_BODY),
    Case("updateTask", ("T-42", {"status": "DONE"}), {}, "/v1/tasks/T-42", {}, {"status": "DONE"}),
    Case("archiveTask", ("T-42",), {}, "/v1/tasks/T-42/archive"),
    Case("unarchiveTask", ("T-42",), {}, "/v1/tasks/T-42/unarchive"),
    Case("listTaskHistory", ("T-42",), {}, "/v1/tasks/T-42/history"),
    Case("getDailyPlan", ({"date": "2026-08-05"},), {}, "/v1/daily-plan", {"date": ["2026-08-05"]}),
    Case(
        "setDailyPlanStatus",
        ({"section": "TODO", "status": "COMPLETED"},),
        {},
        "/v1/daily-plan",
        {},
        {"section": "TODO", "status": "COMPLETED"},
    ),
    Case(
        "createDailyPlanEntry",
        ({"task_id": "T-42", "date": "2026-08-05", "section": "TODO"},),
        {},
        "/v1/daily-plan/entries",
        {},
        {"task_id": "T-42", "date": "2026-08-05", "section": "TODO"},
    ),
    Case(
        "moveDailyPlanEntry",
        ("entry_1", ENTRY_BODY),
        {},
        "/v1/daily-plan/entries/entry_1",
        {},
        ENTRY_BODY,
    ),
    Case("deleteDailyPlanEntry", ("entry_1",), {}, "/v1/daily-plan/entries/entry_1"),
    Case("listTaskAttachments", ("T-42",), {}, "/v1/tasks/T-42/attachments"),
    Case(
        "createAttachmentUpload",
        ("T-42", {"file_name": "a.png", "content_type": "image/png", "size": 12}),
        {},
        "/v1/tasks/T-42/attachments/uploads",
        {},
        {"file_name": "a.png", "content_type": "image/png", "size": 12},
    ),
    Case(
        "createTaskAttachment",
        ("T-42", {"upload_id": "u_1"}),
        {},
        "/v1/tasks/T-42/attachments",
        {},
        {"upload_id": "u_1"},
    ),
    Case("getAttachmentDownloadUrl", ("att_1",), {}, "/v1/attachments/att_1/download-url"),
    Case("listWebhookEndpoints", (), {}, "/v1/webhook-endpoints"),
    Case("getWebhookEndpoint", ("we_1",), {}, "/v1/webhook-endpoints/we_1"),
    Case(
        "createWebhookEndpoint",
        ({"url": "https://example.com/hook", "event_types": ["task.created"]},),
        {},
        "/v1/webhook-endpoints",
        {},
        {"url": "https://example.com/hook", "event_types": ["task.created"]},
    ),
    Case(
        "updateWebhookEndpoint",
        ("we_1", {"enabled": False}),
        {},
        "/v1/webhook-endpoints/we_1",
        {},
        {"enabled": False},
    ),
    Case("deleteWebhookEndpoint", ("we_1",), {}, "/v1/webhook-endpoints/we_1"),
    Case("rotateWebhookEndpointSecret", ("we_1",), {}, "/v1/webhook-endpoints/we_1/rotate-secret"),
    Case("verifyWebhookEndpoint", ("we_1",), {}, "/v1/webhook-endpoints/we_1/verify"),
    Case(
        "testWebhookEndpointEvent",
        ("we_1", {"event_type": "task.created"}),
        {},
        "/v1/webhook-endpoints/we_1/test-event",
        {},
        {"event_type": "task.created"},
    ),
    Case("listWebhookEndpointDeliveries", ("we_1",), {}, "/v1/webhook-endpoints/we_1/deliveries"),
    Case(
        "replayWebhookDelivery",
        ("we_1", "del_1"),
        {},
        "/v1/webhook-endpoints/we_1/deliveries/del_1/replay",
    ),
    Case(
        "replayFailedWebhookDeliveries",
        ("we_1", {"since": "2026-08-01T00:00:00.000Z"}),
        {},
        "/v1/webhook-endpoints/we_1/replay-failed",
        {},
        {"since": "2026-08-01T00:00:00.000Z"},
    ),
]

CASES_BY_ID = {case.operation_id: case for case in CASES}


def spec_path_template(concrete_path: str) -> str | None:
    """Match a concrete request path back to its OpenAPI path template."""
    for _method, template, _idem, _ent in spec_operations().values():
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", template) + "$"
        if re.match(pattern, concrete_path):
            return template
    return None


def mock_everything() -> None:
    respx.route(host="api.test").mock(
        return_value=httpx.Response(200, json={"data": [], "has_more": False, "next_cursor": None})
    )


def test_there_is_a_wire_case_for_every_operation():
    assert set(CASES_BY_ID) == set(OPERATION_MAP)
    assert len(CASES) == 37


@pytest.mark.parametrize("operation_id", sorted(CASES_BY_ID))
@respx.mock
def test_each_sync_method_builds_the_declared_request(operation_id: str):
    case = CASES_BY_ID[operation_id]
    expected_method, expected_template, _idem, _ent = spec_operations()[operation_id]
    mock_everything()

    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        result = resolve(client, OPERATION_MAP[operation_id])(*case.args, **case.kwargs)
        if isinstance(result, Paginator):
            result.page()

    request = respx.calls[0].request
    assert request.method == expected_method
    assert request.url.path == case.expected_path
    # The path the SDK built must be an instance of THIS operation's template.
    assert spec_path_template(request.url.path) == expected_template

    for key, values in case.expected_query.items():
        assert request.url.params.get_list(key) == values

    if case.expected_body is None:
        assert request.content in (b"", b"null")
    else:
        import json

        assert json.loads(request.content) == case.expected_body


@pytest.mark.parametrize("operation_id", sorted(CASES_BY_ID))
@respx.mock
async def test_each_async_method_builds_the_same_request(operation_id: str):
    case = CASES_BY_ID[operation_id]
    expected_method, expected_template, _idem, _ent = spec_operations()[operation_id]
    mock_everything()

    async with AsyncGetItDone(api_key="gid_x", base_url=BASE) as client:
        method = resolve(client, OPERATION_MAP[operation_id])
        result = method(*case.args, **case.kwargs)
        if isinstance(result, AsyncPaginator):
            await result.page()
        else:
            await result

    request = respx.calls[0].request
    assert request.method == expected_method
    assert request.url.path == case.expected_path
    assert spec_path_template(request.url.path) == expected_template


@respx.mock
def test_path_parameters_are_percent_encoded_on_the_wire():
    """An id containing a slash must not silently become two path segments.

    ``URL.path`` is the DECODED view, so the assertion is on ``raw_path`` —
    the bytes actually sent.
    """
    mock_everything()
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.tasks.retrieve("T-1/../admin")

    assert respx.calls[0].request.url.raw_path == b"/v1/tasks/T-1%2F..%2Fadmin"


@respx.mock
def test_path_parameters_with_spaces_and_reserved_characters_are_encoded():
    mock_everything()
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.projects.retrieve("a b&c=d")

    assert respx.calls[0].request.url.raw_path == b"/v1/projects/a%20b%26c%3Dd"


@respx.mock
def test_a_per_call_idempotency_key_reaches_the_wire_on_an_idempotent_method():
    mock_everything()
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.tasks.create(TASK_BODY, idempotency_key="my-key")

    assert respx.calls[0].request.headers["idempotency-key"] == "my-key"


@respx.mock
def test_request_options_survive_alongside_a_per_call_idempotency_key():
    from getitdone_py import RequestOptions

    mock_everything()
    with GetItDone(api_key="gid_x", base_url=BASE) as client:
        client.tasks.create(
            TASK_BODY,
            idempotency_key="my-key",
            options=RequestOptions(headers={"X-Trace": "t1"}),
        )

    request = respx.calls[0].request
    assert request.headers["idempotency-key"] == "my-key"
    assert request.headers["x-trace"] == "t1"
