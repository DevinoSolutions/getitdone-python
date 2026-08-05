"""``/v1/organizations`` — the workspace this credential belongs to."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncOrganizations", "Organizations"]


class Organizations(Resource):
    """Scope: ``workspaces:read``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listOrganizations` — the organization(s) visible to this credential."""
        return self._paginate("GET", "/v1/organizations", query=query, options=options)

    def retrieve(self, organization_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getOrganization` — one organization by id."""
        return self._request(
            "GET",
            f"/v1/organizations/{encode_path_param(organization_id)}",
            options=options,
        )


class AsyncOrganizations(AsyncResource):
    """Async twin of :class:`Organizations`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listOrganizations`"""
        return self._paginate("GET", "/v1/organizations", query=query, options=options)

    async def retrieve(self, organization_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getOrganization`"""
        return await self._request(
            "GET",
            f"/v1/organizations/{encode_path_param(organization_id)}",
            options=options,
        )
