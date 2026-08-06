"""The GetItDone API clients — :class:`GetItDone` and :class:`AsyncGetItDone`.

Thin, hand-owned wrappers over the public ``/v1`` REST surface at
https://app.nowgetitdone.com. They carry a SECRET API key, so they belong on
your server, never in a browser or a shipped mobile binary.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from getitdone_py._http import AsyncHttpCore, HttpCore, HttpMethod, RequestOptions, RequestParams
from getitdone_py.errors import GetItDoneError
from getitdone_py.resources.api_keys import ApiKeys, AsyncApiKeys
from getitdone_py.resources.attachments import AsyncAttachments, Attachments
from getitdone_py.resources.daily_plan import AsyncDailyPlan, DailyPlan
from getitdone_py.resources.members import AsyncMembers, Members
from getitdone_py.resources.organizations import AsyncOrganizations, Organizations
from getitdone_py.resources.projects import AsyncProjects, Projects
from getitdone_py.resources.tasks import AsyncTasks, Tasks
from getitdone_py.resources.usage import AsyncUsage, Usage
from getitdone_py.resources.webhook_endpoints import AsyncWebhookEndpoints, WebhookEndpoints

DEFAULT_BASE_URL = "https://app.nowgetitdone.com"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_RETRY_AFTER_SECONDS = 60.0

API_KEY_ENV_VAR = "GETITDONE_API_KEY"
BASE_URL_ENV_VAR = "GETITDONE_BASE_URL"

MISSING_API_KEY_MESSAGE = (
    "Missing API key: pass `api_key=` to GetItDone(...) or set the "
    "GETITDONE_API_KEY environment variable. "
    "Create one at https://app.nowgetitdone.com/settings (API keys)."
)


def _resolve_api_key(api_key: str | None) -> str:
    resolved = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
    if not resolved:
        raise GetItDoneError(MISSING_API_KEY_MESSAGE)
    return resolved


def _resolve_base_url(base_url: str | None) -> str:
    resolved = base_url or os.environ.get(BASE_URL_ENV_VAR) or DEFAULT_BASE_URL
    return resolved.rstrip("/")


def _user_agent() -> str:
    from getitdone_py import __version__

    return f"getitdone-sdk/{__version__}"


class GetItDone:
    """Synchronous GetItDone API client.

    ::

        from getitdone_py import GetItDone

        with GetItDone() as client:            # reads GETITDONE_API_KEY
            for task in client.tasks.list():
                print(task["title"])
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_retry_after_seconds: float = DEFAULT_MAX_RETRY_AFTER_SECONDS,
        default_headers: dict[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = _resolve_base_url(base_url)
        self._core = HttpCore(
            api_key=_resolve_api_key(api_key),
            base_url=self.base_url,
            timeout=timeout,
            max_retries=max_retries,
            max_retry_after_seconds=max_retry_after_seconds,
            user_agent=_user_agent(),
            default_headers=default_headers,
            http_client=http_client,
        )

        self.organizations = Organizations(self._core)
        self.members = Members(self._core)
        self.projects = Projects(self._core)
        self.tasks = Tasks(self._core)
        self.daily_plan = DailyPlan(self._core)
        self.attachments = Attachments(self._core)
        self.api_keys = ApiKeys(self._core)
        self.webhook_endpoints = WebhookEndpoints(self._core)
        self.usage = Usage(self._core)

    def request(
        self,
        method: HttpMethod,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
        idempotent: bool = False,
        options: RequestOptions | None = None,
    ) -> Any:
        """Raw-request escape hatch: any ``/v1`` call with this client's auth,
        retry and timeout behavior."""
        return self._core.request(
            RequestParams(
                method=method,
                path=path,
                query=query,
                body=body,
                idempotent=idempotent,
                options=options,
            )
        )

    def close(self) -> None:
        self._core.close()

    def __enter__(self) -> GetItDone:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncGetItDone:
    """Asynchronous GetItDone API client.

    ::

        from getitdone_py import AsyncGetItDone

        async with AsyncGetItDone() as client:
            async for task in client.tasks.list():
                print(task["title"])
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_retry_after_seconds: float = DEFAULT_MAX_RETRY_AFTER_SECONDS,
        default_headers: dict[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = _resolve_base_url(base_url)
        self._core = AsyncHttpCore(
            api_key=_resolve_api_key(api_key),
            base_url=self.base_url,
            timeout=timeout,
            max_retries=max_retries,
            max_retry_after_seconds=max_retry_after_seconds,
            user_agent=_user_agent(),
            default_headers=default_headers,
            http_client=http_client,
        )

        self.organizations = AsyncOrganizations(self._core)
        self.members = AsyncMembers(self._core)
        self.projects = AsyncProjects(self._core)
        self.tasks = AsyncTasks(self._core)
        self.daily_plan = AsyncDailyPlan(self._core)
        self.attachments = AsyncAttachments(self._core)
        self.api_keys = AsyncApiKeys(self._core)
        self.webhook_endpoints = AsyncWebhookEndpoints(self._core)
        self.usage = AsyncUsage(self._core)

    async def request(
        self,
        method: HttpMethod,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
        idempotent: bool = False,
        options: RequestOptions | None = None,
    ) -> Any:
        """Raw-request escape hatch (async twin of :meth:`GetItDone.request`)."""
        return await self._core.request(
            RequestParams(
                method=method,
                path=path,
                query=query,
                body=body,
                idempotent=idempotent,
                options=options,
            )
        )

    async def aclose(self) -> None:
        await self._core.aclose()

    async def __aenter__(self) -> AsyncGetItDone:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
