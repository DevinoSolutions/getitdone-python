"""Official Python SDK for the GetItDone public API (``/v1``).

AI-native task management for people and agents — https://nowgetitdone.com

::

    from getitdone_py import GetItDone

    with GetItDone() as client:              # reads GETITDONE_API_KEY
        task = client.tasks.create({"title": "Ship the Python SDK"})
"""

from __future__ import annotations

__version__ = "0.1.0"

from getitdone_py._client import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_RETRY_AFTER_SECONDS,
    DEFAULT_TIMEOUT,
    AsyncGetItDone,
    GetItDone,
)
from getitdone_py._http import RequestOptions
from getitdone_py.errors import (
    PROBLEM_CODES,
    APIConnectionError,
    APIConnectionTimeoutError,
    APIError,
    APIUserAbortError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    FieldError,
    GetItDoneError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    Problem,
    ProblemCode,
    RateLimit,
    RateLimitError,
    RateLimitWindow,
    UnprocessableEntityError,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_RETRY_AFTER_SECONDS",
    "DEFAULT_TIMEOUT",
    "PROBLEM_CODES",
    "APIConnectionError",
    "APIConnectionTimeoutError",
    "APIError",
    "APIUserAbortError",
    "AsyncGetItDone",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "FieldError",
    "GetItDone",
    "GetItDoneError",
    "InternalServerError",
    "NotFoundError",
    "PermissionDeniedError",
    "Problem",
    "ProblemCode",
    "RateLimit",
    "RateLimitError",
    "RateLimitWindow",
    "RequestOptions",
    "UnprocessableEntityError",
    "__version__",
]
