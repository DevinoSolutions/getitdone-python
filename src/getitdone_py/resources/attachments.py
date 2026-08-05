"""Task attachments — a two-phase presigned upload.

``create_upload()`` returns a presigned PUT target, you upload the bytes there
yourself (any HTTP client), then ``create()`` registers the uploaded file on
the task. The SDK deliberately does not proxy the file bytes.
"""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncAttachments", "Attachments"]


class Attachments(Resource):
    """Scopes: ``tasks:read`` / ``tasks:write``."""

    def list(
        self,
        task_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listTaskAttachments`"""
        return self._paginate(
            "GET",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments",
            query=query,
            options=options,
        )

    def create_upload(
        self,
        task_id: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createAttachmentUpload` — phase 1: get the presigned PUT URL."""
        return self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments/uploads",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def create(
        self,
        task_id: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createTaskAttachment` — phase 2: register the uploaded object."""
        return self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def get_download_url(self, attachment_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getAttachmentDownloadUrl` — a short-lived presigned GET URL."""
        return self._request(
            "GET",
            f"/v1/attachments/{encode_path_param(attachment_id)}/download-url",
            options=options,
        )


class AsyncAttachments(AsyncResource):
    """Async twin of :class:`Attachments`."""

    def list(
        self,
        task_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listTaskAttachments`"""
        return self._paginate(
            "GET",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments",
            query=query,
            options=options,
        )

    async def create_upload(
        self,
        task_id: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createAttachmentUpload`"""
        return await self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments/uploads",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def create(
        self,
        task_id: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createTaskAttachment`"""
        return await self._request(
            "POST",
            f"/v1/tasks/{encode_path_param(task_id)}/attachments",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def get_download_url(
        self, attachment_id: str, *, options: RequestOptions | None = None
    ) -> Any:
        """`getAttachmentDownloadUrl`"""
        return await self._request(
            "GET",
            f"/v1/attachments/{encode_path_param(attachment_id)}/download-url",
            options=options,
        )
