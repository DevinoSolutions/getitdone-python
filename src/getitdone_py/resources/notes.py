"""``/v1/notes`` — the workspace's shared notes (not tied to one task)."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncNotes", "Notes"]


class Notes(Resource):
    """Scopes: ``tasks:read`` / ``tasks:write``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listNotes` — each note carries a preview; ``retrieve`` returns the full body."""
        return self._paginate("GET", "/v1/notes", query=query, options=options)

    def retrieve(self, note_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getNote`"""
        return self._request("GET", f"/v1/notes/{encode_path_param(note_id)}", options=options)

    def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createNote` — idempotent; a key is auto-generated when omitted."""
        return self._request(
            "POST",
            "/v1/notes",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def update(
        self, note_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateNote` — ``base_updated_at`` is required; a stale one raises
        :class:`~getitdone_py.ConflictError` (``conflict``) instead of overwriting."""
        return self._request(
            "PATCH", f"/v1/notes/{encode_path_param(note_id)}", body=body, options=options
        )

    def append(
        self, note_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`appendNote` — adds one dated entry to the end; nothing already there changes."""
        return self._request(
            "POST",
            f"/v1/notes/{encode_path_param(note_id)}/append",
            body=body,
            options=options,
        )


class AsyncNotes(AsyncResource):
    """Async twin of :class:`Notes`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listNotes`"""
        return self._paginate("GET", "/v1/notes", query=query, options=options)

    async def retrieve(self, note_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getNote`"""
        return await self._request(
            "GET", f"/v1/notes/{encode_path_param(note_id)}", options=options
        )

    async def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createNote`"""
        return await self._request(
            "POST",
            "/v1/notes",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def update(
        self, note_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateNote`"""
        return await self._request(
            "PATCH", f"/v1/notes/{encode_path_param(note_id)}", body=body, options=options
        )

    async def append(
        self, note_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`appendNote`"""
        return await self._request(
            "POST",
            f"/v1/notes/{encode_path_param(note_id)}/append",
            body=body,
            options=options,
        )
