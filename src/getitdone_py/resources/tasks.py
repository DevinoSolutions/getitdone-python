"""``/v1/tasks`` — the core resource. Task ids are public short ids, e.g. ``T-42``."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncTasks", "Tasks"]


class Tasks(Resource):
    """Scopes: ``tasks:read`` / ``tasks:write``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listTasks`"""
        return self._paginate("GET", "/v1/tasks", query=query, options=options)

    def retrieve(self, task_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getTask`"""
        return self._request("GET", f"/v1/tasks/{encode_path_param(task_id)}", options=options)

    def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createTask` — idempotent; a key is auto-generated when omitted."""
        return self._request(
            "POST",
            "/v1/tasks",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def update(
        self, task_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateTask` — absolute-set semantics (no increments), so retry-safe."""
        return self._request(
            "PATCH", f"/v1/tasks/{encode_path_param(task_id)}", body=body, options=options
        )

    def archive(
        self,
        task_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`archiveTask`"""
        return self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/archive",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def unarchive(
        self,
        task_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`unarchiveTask`"""
        return self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/unarchive",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def list_history(
        self,
        task_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listTaskHistory` — version history, newest first."""
        return self._paginate(
            "GET",
            f"/v1/tasks/{encode_path_param(task_id)}/history",
            query=query,
            options=options,
        )


class AsyncTasks(AsyncResource):
    """Async twin of :class:`Tasks`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listTasks`"""
        return self._paginate("GET", "/v1/tasks", query=query, options=options)

    async def retrieve(self, task_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getTask`"""
        return await self._request(
            "GET", f"/v1/tasks/{encode_path_param(task_id)}", options=options
        )

    async def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createTask`"""
        return await self._request(
            "POST",
            "/v1/tasks",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def update(
        self, task_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateTask`"""
        return await self._request(
            "PATCH", f"/v1/tasks/{encode_path_param(task_id)}", body=body, options=options
        )

    async def archive(
        self,
        task_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`archiveTask`"""
        return await self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/archive",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def unarchive(
        self,
        task_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`unarchiveTask`"""
        return await self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/unarchive",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def list_history(
        self,
        task_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listTaskHistory`"""
        return self._paginate(
            "GET",
            f"/v1/tasks/{encode_path_param(task_id)}/history",
            query=query,
            options=options,
        )
