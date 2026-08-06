"""``/v1/daily-plan`` — the daily board (``TODO`` / ``PROGRESS`` sections)."""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncDailyPlan", "DailyPlan"]


class DailyPlan(Resource):
    """Scopes: ``tasks:read`` / ``tasks:write``."""

    def retrieve(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Any:
        """`getDailyPlan` — the board for a date.

        ``query["date"]`` is REQUIRED (``YYYY-MM-DD``). There is no server-side
        "today" default: omitting it returns 400 ``validation_failed`` with an
        error pointer of ``/date``.
        """
        return self._request("GET", "/v1/daily-plan", query=query, options=options)

    def set_status(
        self,
        body: dict[str, Any],
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Any:
        """`setDailyPlanStatus`"""
        return self._request("PATCH", "/v1/daily-plan", query=query, body=body, options=options)

    def create_entry(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createDailyPlanEntry` — idempotent."""
        return self._request(
            "POST",
            "/v1/daily-plan/entries",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def move_entry(
        self, entry_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`moveDailyPlanEntry` — the server RECREATES the entry, so the result
        carries a NEW id."""
        return self._request(
            "PATCH",
            f"/v1/daily-plan/entries/{encode_path_param(entry_id)}",
            body=body,
            options=options,
        )

    def delete_entry(self, entry_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteDailyPlanEntry`"""
        return self._request(
            "DELETE",
            f"/v1/daily-plan/entries/{encode_path_param(entry_id)}",
            options=options,
        )


class AsyncDailyPlan(AsyncResource):
    """Async twin of :class:`DailyPlan`."""

    async def retrieve(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Any:
        """`getDailyPlan` — ``query["date"]`` is REQUIRED; see :meth:`DailyPlan.retrieve`."""
        return await self._request("GET", "/v1/daily-plan", query=query, options=options)

    async def set_status(
        self,
        body: dict[str, Any],
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Any:
        """`setDailyPlanStatus`"""
        return await self._request(
            "PATCH", "/v1/daily-plan", query=query, body=body, options=options
        )

    async def create_entry(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createDailyPlanEntry`"""
        return await self._request(
            "POST",
            "/v1/daily-plan/entries",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def move_entry(
        self, entry_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`moveDailyPlanEntry`"""
        return await self._request(
            "PATCH",
            f"/v1/daily-plan/entries/{encode_path_param(entry_id)}",
            body=body,
            options=options,
        )

    async def delete_entry(self, entry_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteDailyPlanEntry`"""
        return await self._request(
            "DELETE",
            f"/v1/daily-plan/entries/{encode_path_param(entry_id)}",
            options=options,
        )
