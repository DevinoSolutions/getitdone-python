"""Real end-to-end smoke against https://app.nowgetitdone.com.

Gated on ``GETITDONE_API_KEY``. When it is absent these tests SKIP LOUDLY rather
than passing silently — a skipped e2e is not a green e2e.

Every fixture this creates is titled with the ``[[sdk-smoke]]`` prefix and is
archived on teardown, so a run leaves production clean.
"""

from __future__ import annotations

import contextlib
import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from getitdone_py import (
    AsyncGetItDone,
    GetItDone,
    PermissionDeniedError,
)
from getitdone_py.errors import parse_rate_limit

PROD_BASE_URL = "https://app.nowgetitdone.com"
API_KEY = os.environ.get("GETITDONE_API_KEY")
TITLE_PREFIX = "[[sdk-smoke]]"

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason=(
        "LOUD SKIP: GETITDONE_API_KEY is not set, so the authenticated prod smoke "
        "cannot run. Set it to an organization API key with scopes "
        "workspaces:read, members:read, projects:read, projects:write, tasks:read, "
        "tasks:write, usage:read, webhooks:read to exercise the real read/write/"
        "idempotency round trip. (tests/e2e/test_unauthenticated_prod.py still runs "
        "without any credential.)"
    ),
)


@pytest.fixture(scope="module")
def client() -> Iterator[GetItDone]:
    with GetItDone(api_key=API_KEY, base_url=PROD_BASE_URL) as sdk:
        yield sdk


@pytest.fixture
def smoke_task(client: GetItDone) -> Iterator[dict[str, Any]]:
    """A throwaway task, archived again on teardown."""
    task = client.tasks.create({"title": f"{TITLE_PREFIX} {uuid.uuid4()}"})
    try:
        yield task
    finally:
        # Teardown must never mask the real failure the test is reporting.
        with contextlib.suppress(Exception):
            client.tasks.archive(task["id"])


class TestReadPaths:
    def test_organizations_list_returns_the_credentials_organization(self, client: GetItDone):
        organizations = list(client.organizations.list())
        assert len(organizations) >= 1
        assert organizations[0]["id"]
        assert organizations[0]["name"]

    def test_an_organization_can_be_retrieved_by_id(self, client: GetItDone):
        organization = next(iter(client.organizations.list()))
        fetched = client.organizations.retrieve(organization["id"])
        assert fetched["id"] == organization["id"]

    def test_usage_reports_the_plan_and_its_meters(self, client: GetItDone):
        usage = client.usage.retrieve()
        assert usage["plan"]
        assert isinstance(usage["meters"], list)
        assert usage["meters"], "at least the API_CALLS meter should be present"

    def test_members_list_is_reachable(self, client: GetItDone):
        assert isinstance(client.members.list({"limit": 5}).page().data, list)

    def test_projects_list_is_reachable(self, client: GetItDone):
        assert isinstance(client.projects.list({"limit": 5}).page().data, list)

    def test_tasks_list_returns_typed_task_shapes(self, client: GetItDone):
        from getitdone_py.models import Task

        page = client.tasks.list({"limit": 2}).page()
        for task in page.data:
            Task.model_validate(task)

    def test_the_daily_plan_is_reachable(self, client: GetItDone):
        plan = client.daily_plan.retrieve()
        assert "date" in plan
        assert "sections" in plan


class TestPagination:
    def test_a_one_item_page_size_walks_multiple_requests(self, client: GetItDone):
        collected: list[dict[str, Any]] = []
        for task in client.tasks.list({"limit": 1}):
            collected.append(task)
            if len(collected) == 3:
                break

        if len(collected) < 3:
            pytest.skip(f"organization has only {len(collected)} tasks — need 3 to walk pages")

        ids = [task["id"] for task in collected]
        assert len(set(ids)) == 3, "pagination returned duplicates across pages"

    def test_a_page_reports_its_cursor_state(self, client: GetItDone):
        page = client.tasks.list({"limit": 1}).page()
        assert isinstance(page.has_more, bool)
        if page.has_more:
            assert page.next_cursor
            assert page.get_next_page() is not None


class TestWriteAndIdempotency:
    def test_the_same_idempotency_key_replays_instead_of_creating_twice(self, client: GetItDone):
        from getitdone_py._http import RequestOptions, RequestParams

        key = f"sdk-smoke-{uuid.uuid4()}"
        body = {"title": f"{TITLE_PREFIX} idempotency {uuid.uuid4()}"}

        def create() -> Any:
            return client._core.request_with_response(
                RequestParams(
                    method="POST",
                    path="/v1/tasks",
                    body=body,
                    idempotent=True,
                    options=RequestOptions(idempotency_key=key),
                )
            )

        first = create()
        second = create()
        try:
            assert first.data["id"] == second.data["id"], "the replay returned a different task"
            assert second.replayed is True, "the second call was not marked idempotency-replayed"
        finally:
            client.tasks.archive(first.data["id"])

    def test_a_task_round_trips_through_update_history_archive_and_unarchive(
        self, client: GetItDone, smoke_task: dict[str, Any]
    ):
        task_id = smoke_task["id"]
        assert task_id.startswith("T-")

        updated = client.tasks.update(task_id, {"status": "DONE"})
        assert updated["status"] == "DONE"

        assert client.tasks.retrieve(task_id)["status"] == "DONE"

        history = client.tasks.list_history(task_id).page()
        assert isinstance(history.data, list)

        archived = client.tasks.archive(task_id)
        assert archived["id"] == task_id

        unarchived = client.tasks.unarchive(task_id)
        assert unarchived["id"] == task_id


class TestTransportContract:
    def test_rate_limit_headers_are_present_on_a_successful_response(self, client: GetItDone):
        from getitdone_py._http import RequestParams

        response = client._core.request_with_response(RequestParams(method="GET", path="/v1/usage"))
        assert response.status_code == 200

        rate_limit = parse_rate_limit(response.headers)
        assert rate_limit.windows, "no RateLimit-Policy / RateLimit windows on a 200"
        assert rate_limit.limit is not None, "no X-RateLimit-Limit on a 200"
        assert rate_limit.remaining is not None


class TestEntitlements:
    def test_webhook_endpoints_either_list_or_report_the_plan_gate(self, client: GetItDone):
        """Both outcomes are CORRECT: a PRO+ key lists endpoints, a lower plan
        gets 403 feature_not_enabled. Anything else is a bug."""
        try:
            page = client.webhook_endpoints.list({"limit": 5}).page()
        except PermissionDeniedError as error:
            assert error.code == "feature_not_enabled", (
                f"unexpected 403 code on a webhook read: {error.code}"
            )
        else:
            assert isinstance(page.data, list)


class TestAsyncClient:
    async def test_the_async_client_reads_and_paginates_against_prod(self):
        async with AsyncGetItDone(api_key=API_KEY, base_url=PROD_BASE_URL) as client:
            usage = await client.usage.retrieve()
            assert usage["plan"]

            organizations = [org async for org in client.organizations.list()]
            assert len(organizations) >= 1
