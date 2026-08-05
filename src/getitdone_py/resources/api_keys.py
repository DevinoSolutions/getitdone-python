"""``/v1/api-keys`` — organization API key management."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["ApiKeys", "AsyncApiKeys"]


class ApiKeys(Resource):
    """Scope: ``api-keys:manage``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listApiKeys` — key metadata only; plaintext is never returned again."""
        return self._paginate("GET", "/v1/api-keys", query=query, options=options)

    def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createApiKey` — the response includes the plaintext key SHOWN ONCE."""
        return self._request(
            "POST",
            "/v1/api-keys",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def delete(self, key_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteApiKey` — revoke a key."""
        return self._request("DELETE", f"/v1/api-keys/{encode_path_param(key_id)}", options=options)


class AsyncApiKeys(AsyncResource):
    """Async twin of :class:`ApiKeys`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listApiKeys`"""
        return self._paginate("GET", "/v1/api-keys", query=query, options=options)

    async def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createApiKey`"""
        return await self._request(
            "POST",
            "/v1/api-keys",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def delete(self, key_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteApiKey`"""
        return await self._request(
            "DELETE", f"/v1/api-keys/{encode_path_param(key_id)}", options=options
        )
