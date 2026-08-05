"""Shared plumbing for every resource namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from getitdone_py._http import HttpMethod, RequestOptions, RequestParams, encode_path_param
from getitdone_py._pagination import AsyncPaginator, Paginator

if TYPE_CHECKING:
    from getitdone_py._http import AsyncHttpCore, HttpCore

__all__ = ["AsyncResource", "Resource", "encode_path_param"]


def _params(
    method: HttpMethod,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: Any = None,
    idempotent: bool = False,
    options: RequestOptions | None = None,
    idempotency_key: str | None = None,
) -> RequestParams:
    if idempotency_key is not None:
        options = options or RequestOptions()
        options = RequestOptions(
            idempotency_key=idempotency_key,
            timeout=options.timeout,
            max_retries=options.max_retries,
            headers=dict(options.headers),
        )
    return RequestParams(
        method=method,
        path=path,
        query=query,
        body=body,
        idempotent=idempotent,
        options=options,
    )


class Resource:
    """Base for every sync resource namespace — holds the shared request engine."""

    def __init__(self, core: HttpCore):
        self._core = core

    def _request(self, *args: Any, **kwargs: Any) -> Any:
        return self._core.request(_params(*args, **kwargs))

    def _paginate(self, *args: Any, **kwargs: Any) -> Paginator[Any]:
        return Paginator(self._core, _params(*args, **kwargs))


class AsyncResource:
    """Base for every async resource namespace."""

    def __init__(self, core: AsyncHttpCore):
        self._core = core

    async def _request(self, *args: Any, **kwargs: Any) -> Any:
        return await self._core.request(_params(*args, **kwargs))

    def _paginate(self, *args: Any, **kwargs: Any) -> AsyncPaginator[Any]:
        return AsyncPaginator(self._core, _params(*args, **kwargs))
