"""``/v1/usage`` — billing-period meters, plan id and burst policy."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py.resources._base import AsyncResource, Resource

__all__ = ["AsyncUsage", "Usage"]


class Usage(Resource):
    """Scope: ``usage:read``. The only operation metered at cost 0."""

    def retrieve(self, *, options: RequestOptions | None = None) -> Any:
        """`getUsage` — current billing-period usage per meter."""
        return self._request("GET", "/v1/usage", options=options)


class AsyncUsage(AsyncResource):
    """Async twin of :class:`Usage`."""

    async def retrieve(self, *, options: RequestOptions | None = None) -> Any:
        """`getUsage`"""
        return await self._request("GET", "/v1/usage", options=options)
