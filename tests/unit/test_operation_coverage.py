"""The mechanical parity gate: every spec operation has exactly one SDK method.

This is the test that guarantees 37/37 endpoint coverage and goes RED the day
the API adds a 38th route — a missing binding cannot ship unnoticed.

``OPERATION_MAP`` is written by hand on purpose. It is the explicit claim
"operationId X is reachable as client.<this>", checked against the vendored
spec, not derived from it.
"""

from __future__ import annotations

import inspect

import pytest

from getitdone_py import AsyncGetItDone, GetItDone
from tests.helpers import spec_operations

#: operationId -> the dotted SDK accessor on a client instance.
OPERATION_MAP: dict[str, str] = {
    "listOrganizations": "organizations.list",
    "getOrganization": "organizations.retrieve",
    "getUsage": "usage.retrieve",
    "listMembers": "members.list",
    "listProjects": "projects.list",
    "getProject": "projects.retrieve",
    "createProject": "projects.create",
    "listApiKeys": "api_keys.list",
    "createApiKey": "api_keys.create",
    "deleteApiKey": "api_keys.delete",
    "listTasks": "tasks.list",
    "getTask": "tasks.retrieve",
    "createTask": "tasks.create",
    "updateTask": "tasks.update",
    "archiveTask": "tasks.archive",
    "unarchiveTask": "tasks.unarchive",
    "listTaskHistory": "tasks.list_history",
    "getDailyPlan": "daily_plan.retrieve",
    "setDailyPlanStatus": "daily_plan.set_status",
    "createDailyPlanEntry": "daily_plan.create_entry",
    "moveDailyPlanEntry": "daily_plan.move_entry",
    "deleteDailyPlanEntry": "daily_plan.delete_entry",
    "listTaskAttachments": "attachments.list",
    "createAttachmentUpload": "attachments.create_upload",
    "createTaskAttachment": "attachments.create",
    "getAttachmentDownloadUrl": "attachments.get_download_url",
    "listWebhookEndpoints": "webhook_endpoints.list",
    "getWebhookEndpoint": "webhook_endpoints.retrieve",
    "createWebhookEndpoint": "webhook_endpoints.create",
    "updateWebhookEndpoint": "webhook_endpoints.update",
    "deleteWebhookEndpoint": "webhook_endpoints.delete",
    "rotateWebhookEndpointSecret": "webhook_endpoints.rotate_secret",
    "verifyWebhookEndpoint": "webhook_endpoints.verify",
    "testWebhookEndpointEvent": "webhook_endpoints.test_event",
    "listWebhookEndpointDeliveries": "webhook_endpoints.list_deliveries",
    "replayWebhookDelivery": "webhook_endpoints.replay_delivery",
    "replayFailedWebhookDeliveries": "webhook_endpoints.replay_failed",
}


def resolve(client: object, accessor: str) -> object:
    target = client
    for part in accessor.split("."):
        target = getattr(target, part)
    return target


@pytest.fixture
def client() -> GetItDone:
    return GetItDone(api_key="gid_x", base_url="https://api.test")


@pytest.fixture
def async_client() -> AsyncGetItDone:
    return AsyncGetItDone(api_key="gid_x", base_url="https://api.test")


def test_the_spec_still_declares_exactly_thirty_seven_operations():
    assert len(spec_operations()) == 37


def test_the_operation_map_covers_every_spec_operation_and_invents_none():
    spec_ids = set(spec_operations())
    mapped = set(OPERATION_MAP)
    assert mapped - spec_ids == set(), "OPERATION_MAP names operations the spec does not have"
    assert spec_ids - mapped == set(), "spec operations with no SDK method"
    assert len(OPERATION_MAP) == 37


def test_every_operation_maps_to_a_distinct_sdk_method():
    assert len(set(OPERATION_MAP.values())) == 37


@pytest.mark.parametrize("operation_id", sorted(OPERATION_MAP))
def test_every_operation_is_bound_and_callable_on_the_sync_client(
    client: GetItDone, operation_id: str
):
    method = resolve(client, OPERATION_MAP[operation_id])
    assert callable(method), f"{OPERATION_MAP[operation_id]} is not callable"


@pytest.mark.parametrize("operation_id", sorted(OPERATION_MAP))
def test_every_operation_is_bound_and_callable_on_the_async_client(
    async_client: AsyncGetItDone, operation_id: str
):
    method = resolve(async_client, OPERATION_MAP[operation_id])
    assert callable(method), f"{OPERATION_MAP[operation_id]} is not callable"


def test_the_nine_paginated_operations_return_a_paginator_type(client: GetItDone):
    """The 9 cursor-paginated lists — everything else returns data directly."""
    paginated = {
        "listOrganizations",
        "listMembers",
        "listProjects",
        "listApiKeys",
        "listTasks",
        "listTaskHistory",
        "listTaskAttachments",
        "listWebhookEndpoints",
        "listWebhookEndpointDeliveries",
    }
    assert len(paginated) == 9
    assert paginated <= set(OPERATION_MAP)

    for operation_id in paginated:
        method = resolve(client, OPERATION_MAP[operation_id])
        annotation = inspect.signature(method).return_annotation
        assert "Paginator" in str(annotation), f"{operation_id} does not return a Paginator"


def test_only_the_ten_idempotent_operations_expose_an_idempotency_key_argument(
    client: GetItDone,
):
    with_key = set()
    for operation_id, accessor in OPERATION_MAP.items():
        method = resolve(client, accessor)
        if "idempotency_key" in inspect.signature(method).parameters:
            with_key.add(operation_id)

    declared = {op for op, (_, _, idempotent, _) in spec_operations().items() if idempotent}
    assert with_key == declared
    assert len(with_key) == 10
