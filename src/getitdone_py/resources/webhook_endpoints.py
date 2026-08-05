"""``/v1/webhook-endpoints`` — outbound Standard-Webhooks delivery.

All 11 operations sit behind the ``outbound_webhooks`` entitlement: a Free or
Starter key gets ``403 feature_not_enabled``
(:class:`~getitdone_py.PermissionDeniedError` with
``code == "feature_not_enabled"``), which is correct behavior, not a bug.
Verify inbound deliveries with :mod:`getitdone_py.webhooks`.
"""

from __future__ import annotations

from typing import Any

from getitdone_py._http import RequestOptions
from getitdone_py._pagination import AsyncPaginator, Paginator
from getitdone_py.resources._base import AsyncResource, Resource, encode_path_param

__all__ = ["AsyncWebhookEndpoints", "WebhookEndpoints"]


class WebhookEndpoints(Resource):
    """Scopes: ``webhooks:read`` / ``webhooks:write``. PRO+ only."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listWebhookEndpoints`"""
        return self._paginate("GET", "/v1/webhook-endpoints", query=query, options=options)

    def retrieve(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getWebhookEndpoint`"""
        return self._request(
            "GET", f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}", options=options
        )

    def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createWebhookEndpoint` — the response carries the ``whsec_`` signing
        secret, SHOWN ONCE."""
        return self._request(
            "POST",
            "/v1/webhook-endpoints",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def update(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateWebhookEndpoint`"""
        return self._request(
            "PATCH",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}",
            body=body,
            options=options,
        )

    def delete(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteWebhookEndpoint`"""
        return self._request(
            "DELETE", f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}", options=options
        )

    def rotate_secret(
        self,
        endpoint_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`rotateWebhookEndpointSecret` — the previous secret keeps signing for
        the grace window, so mid-rotation deliveries carry TWO signatures."""
        return self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/rotate-secret",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    def verify(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`verifyWebhookEndpoint` — a live signed probe through the SSRF
        gauntlet. Deliberately NOT idempotent: every call is a fresh probe, so
        the SDK never retries it."""
        return self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/verify",
            options=options,
        )

    def test_event(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`testWebhookEndpointEvent` — send a signed test event (live probe,
        never retried)."""
        return self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/test-event",
            body=body,
            options=options,
        )

    def list_deliveries(
        self,
        endpoint_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> Paginator[Any]:
        """`listWebhookEndpointDeliveries`"""
        return self._paginate(
            "GET",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/deliveries",
            query=query,
            options=options,
        )

    def replay_delivery(
        self, endpoint_id: str, delivery_id: str, *, options: RequestOptions | None = None
    ) -> Any:
        """`replayWebhookDelivery` — re-queue ONE terminal delivery. Answers 409
        ``delivery_already_pending`` when one is already queued, which is what
        makes a double-click safe; carries no Idempotency-Key."""
        return self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}"
            f"/deliveries/{encode_path_param(delivery_id)}/replay",
            options=options,
        )

    def replay_failed(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`replayFailedWebhookDeliveries` — bulk-replay FAILED/DISABLED
        deliveries created at or after ``since`` (capped at 1000/call)."""
        return self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/replay-failed",
            body=body,
            options=options,
        )


class AsyncWebhookEndpoints(AsyncResource):
    """Async twin of :class:`WebhookEndpoints`."""

    def list(
        self,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listWebhookEndpoints`"""
        return self._paginate("GET", "/v1/webhook-endpoints", query=query, options=options)

    async def retrieve(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`getWebhookEndpoint`"""
        return await self._request(
            "GET", f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}", options=options
        )

    async def create(
        self,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`createWebhookEndpoint`"""
        return await self._request(
            "POST",
            "/v1/webhook-endpoints",
            body=body,
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def update(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`updateWebhookEndpoint`"""
        return await self._request(
            "PATCH",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}",
            body=body,
            options=options,
        )

    async def delete(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`deleteWebhookEndpoint`"""
        return await self._request(
            "DELETE", f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}", options=options
        )

    async def rotate_secret(
        self,
        endpoint_id: str,
        *,
        idempotency_key: str | None = None,
        options: RequestOptions | None = None,
    ) -> Any:
        """`rotateWebhookEndpointSecret`"""
        return await self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/rotate-secret",
            idempotent=True,
            idempotency_key=idempotency_key,
            options=options,
        )

    async def verify(self, endpoint_id: str, *, options: RequestOptions | None = None) -> Any:
        """`verifyWebhookEndpoint`"""
        return await self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/verify",
            options=options,
        )

    async def test_event(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`testWebhookEndpointEvent`"""
        return await self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/test-event",
            body=body,
            options=options,
        )

    def list_deliveries(
        self,
        endpoint_id: str,
        query: dict[str, Any] | None = None,
        *,
        options: RequestOptions | None = None,
    ) -> AsyncPaginator[Any]:
        """`listWebhookEndpointDeliveries`"""
        return self._paginate(
            "GET",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/deliveries",
            query=query,
            options=options,
        )

    async def replay_delivery(
        self, endpoint_id: str, delivery_id: str, *, options: RequestOptions | None = None
    ) -> Any:
        """`replayWebhookDelivery`"""
        return await self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}"
            f"/deliveries/{encode_path_param(delivery_id)}/replay",
            options=options,
        )

    async def replay_failed(
        self, endpoint_id: str, body: dict[str, Any], *, options: RequestOptions | None = None
    ) -> Any:
        """`replayFailedWebhookDeliveries`"""
        return await self._request(
            "POST",
            f"/v1/webhook-endpoints/{encode_path_param(endpoint_id)}/replay-failed",
            body=body,
            options=options,
        )
