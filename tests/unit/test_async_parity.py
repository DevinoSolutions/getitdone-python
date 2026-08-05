"""Every sync resource method must have an async twin with the SAME signature.

Introspection-driven, so a method added to one client and forgotten on the
other fails here rather than in a user's code.
"""

from __future__ import annotations

import inspect

import pytest

from getitdone_py import AsyncGetItDone, GetItDone

RESOURCE_NAMES = [
    "organizations",
    "members",
    "projects",
    "tasks",
    "daily_plan",
    "attachments",
    "api_keys",
    "webhook_endpoints",
    "usage",
]


@pytest.fixture
def clients() -> tuple[GetItDone, AsyncGetItDone]:
    return (
        GetItDone(api_key="gid_x", base_url="https://api.test"),
        AsyncGetItDone(api_key="gid_x", base_url="https://api.test"),
    )


def public_methods(resource: object) -> dict[str, object]:
    return {
        name: getattr(resource, name)
        for name in dir(resource)
        if not name.startswith("_") and callable(getattr(resource, name))
    }


def test_both_clients_expose_the_same_nine_resource_namespaces(
    clients: tuple[GetItDone, AsyncGetItDone],
):
    sync_client, async_client = clients
    for name in RESOURCE_NAMES:
        assert hasattr(sync_client, name), f"sync client is missing {name}"
        assert hasattr(async_client, name), f"async client is missing {name}"

    sync_namespaces = {n for n in vars(sync_client) if not n.startswith("_") and n != "base_url"}
    assert sync_namespaces == set(RESOURCE_NAMES)


@pytest.mark.parametrize("resource_name", RESOURCE_NAMES)
def test_each_resource_has_the_same_method_names_on_both_clients(
    clients: tuple[GetItDone, AsyncGetItDone], resource_name: str
):
    sync_client, async_client = clients
    sync_methods = set(public_methods(getattr(sync_client, resource_name)))
    async_methods = set(public_methods(getattr(async_client, resource_name)))
    assert sync_methods == async_methods


@pytest.mark.parametrize("resource_name", RESOURCE_NAMES)
def test_every_twin_has_an_identical_signature(
    clients: tuple[GetItDone, AsyncGetItDone], resource_name: str
):
    sync_client, async_client = clients
    sync_resource = getattr(sync_client, resource_name)
    async_resource = getattr(async_client, resource_name)

    for name, sync_method in public_methods(sync_resource).items():
        async_method = getattr(async_resource, name)
        sync_signature = inspect.signature(sync_method)
        async_signature = inspect.signature(async_method)

        assert list(sync_signature.parameters) == list(async_signature.parameters), (
            f"{resource_name}.{name} parameter names differ"
        )
        for parameter_name, sync_parameter in sync_signature.parameters.items():
            async_parameter = async_signature.parameters[parameter_name]
            assert sync_parameter.kind == async_parameter.kind
            assert sync_parameter.default == async_parameter.default
            assert str(sync_parameter.annotation) == str(async_parameter.annotation)


@pytest.mark.parametrize("resource_name", RESOURCE_NAMES)
def test_non_list_twins_are_coroutines_and_list_twins_are_not(
    clients: tuple[GetItDone, AsyncGetItDone], resource_name: str
):
    """List methods return a paginator SYNCHRONOUSLY on both clients — you
    ``async for`` the result, you do not await the call itself."""
    _sync_client, async_client = clients
    async_resource = getattr(async_client, resource_name)

    for name, method in public_methods(async_resource).items():
        is_list = name.startswith("list")
        assert inspect.iscoroutinefunction(method) is not is_list, (
            f"{resource_name}.{name} has the wrong async shape"
        )


def test_both_clients_expose_the_raw_request_escape_hatch(
    clients: tuple[GetItDone, AsyncGetItDone],
):
    sync_client, async_client = clients
    assert list(inspect.signature(sync_client.request).parameters) == list(
        inspect.signature(async_client.request).parameters
    )
    assert inspect.iscoroutinefunction(async_client.request)
    assert not inspect.iscoroutinefunction(sync_client.request)
