"""``/v1/members`` — organization membership."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource

__all__ = ["AsyncMembers", "Members"]


class Members(Resource):
    """Scope: ``members:read``."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listMembers` — every member of the credential's organization."""
        return self._paginate("GET", "/v1/members", query=query, options=options)


class AsyncMembers(AsyncResource):
    """Async twin of :class:`Members`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listMembers`"""
        return self._paginate("GET", "/v1/members", query=query, options=options)
