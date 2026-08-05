"""``/v1/projects``."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncProjects", "Projects"]


class Projects(Resource):
    """Scopes: ``projects:read`` / ``projects:write``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listProjects`"""
        return self._paginate("GET", "/v1/projects", query=query, options=options)

    def retrieve(self, project_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getProject`"""
        return self._request(
            "GET", f"/v1/projects/{encode_path_param(project_id)}", options=options
        )

    def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createProject` — idempotent; a key is auto-generated when omitted."""
        return self._request(
            "POST",
            "/v1/projects",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )


class AsyncProjects(AsyncResource):
    """Async twin of :class:`Projects`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listProjects`"""
        return self._paginate("GET", "/v1/projects", query=query, options=options)

    async def retrieve(self, project_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getProject`"""
        return await self._request(
            "GET", f"/v1/projects/{encode_path_param(project_id)}", options=options
        )

    async def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createProject`"""
        return await self._request(
            "POST",
            "/v1/projects",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )
