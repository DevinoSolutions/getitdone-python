"""Cursor pagination for the 9 paginated ``/v1`` list operations.

Every list responds with ``{data, has_more, next_cursor}``; the next page is the
SAME query plus ``after=next_cursor``. The server REJECTS a cursor reused with
different query params (``400 validation_failed``), so :class:`Page` re-sends
the original query verbatim and only swaps the cursor.

Two consumption styles:

* auto-iteration — ``for task in client.tasks.list()`` walks every page;
* page escape hatch — ``page = client.tasks.list().page()`` then ``page.data`` /
  ``page.get_next_page()``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from getitdone_py._http import RequestParams

if TYPE_CHECKING:
    from getitdone_py._http import AsyncHttpCore, HttpCore

Item = TypeVar("Item")

__all__ = ["AsyncPage", "AsyncPaginator", "Page", "Paginator"]


def _envelope(payload: Any) -> tuple[list[Any], bool, str | None]:
    if not isinstance(payload, dict):
        return [], False, None
    data = payload.get("data") or []
    return list(data), bool(payload.get("has_more", False)), payload.get("next_cursor")


def _next_params(params: RequestParams, cursor: str) -> RequestParams:
    return replace(params, query={**(params.query or {}), "after": cursor})


class Page(Generic[Item]):
    """One page of results, plus the handle to fetch the next one."""

    def __init__(self, core: HttpCore, params: RequestParams, payload: Any):
        self._core = core
        self._params = params
        data, has_more, next_cursor = _envelope(payload)
        #: The items on this page.
        self.data: list[Item] = data
        #: True when another page exists after this one.
        self.has_more: bool = has_more
        #: Opaque cursor for the next page; ``None`` on the last page.
        self.next_cursor: str | None = next_cursor

    def get_next_page(self) -> Page[Item] | None:
        """Fetch the next page with the SAME query, or ``None`` on the last page."""
        if not self.has_more or self.next_cursor is None:
            return None
        params = _next_params(self._params, self.next_cursor)
        return Page(self._core, params, self._core.request(params))

    def __iter__(self) -> Iterator[Item]:
        """Iterate this page's items, then every following page's."""
        page: Page[Item] | None = self
        while page is not None:
            yield from page.data
            page = page.get_next_page()

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"<Page items={len(self.data)} has_more={self.has_more}>"


class Paginator(Generic[Item]):
    """Lazy handle returned by every sync list method.

    Iterating it streams items across pages; :meth:`page` gives the raw first
    page when you want to drive the cursor yourself.
    """

    def __init__(self, core: HttpCore, params: RequestParams):
        self._core = core
        self._params = params

    def page(self) -> Page[Item]:
        """Fetch just the first page."""
        return Page(self._core, self._params, self._core.request(self._params))

    def __iter__(self) -> Iterator[Item]:
        return iter(self.page())

    def __repr__(self) -> str:
        return f"<Paginator {self._params.method} {self._params.path}>"


class AsyncPage(Generic[Item]):
    """Async twin of :class:`Page`."""

    def __init__(self, core: AsyncHttpCore, params: RequestParams, payload: Any):
        self._core = core
        self._params = params
        data, has_more, next_cursor = _envelope(payload)
        self.data: list[Item] = data
        self.has_more: bool = has_more
        self.next_cursor: str | None = next_cursor

    async def get_next_page(self) -> AsyncPage[Item] | None:
        if not self.has_more or self.next_cursor is None:
            return None
        params = _next_params(self._params, self.next_cursor)
        return AsyncPage(self._core, params, await self._core.request(params))

    async def __aiter__(self) -> AsyncIterator[Item]:
        page: AsyncPage[Item] | None = self
        while page is not None:
            for item in page.data:
                yield item
            page = await page.get_next_page()

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"<AsyncPage items={len(self.data)} has_more={self.has_more}>"


class AsyncPaginator(Generic[Item]):
    """Async twin of :class:`Paginator` — ``async for item in client.tasks.list()``."""

    def __init__(self, core: AsyncHttpCore, params: RequestParams):
        self._core = core
        self._params = params

    async def page(self) -> AsyncPage[Item]:
        return AsyncPage(self._core, self._params, await self._core.request(self._params))

    async def __aiter__(self) -> AsyncIterator[Item]:
        page = await self.page()
        async for item in page:
            yield item

    def __repr__(self) -> str:
        return f"<AsyncPaginator {self._params.method} {self._params.path}>"
