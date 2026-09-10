"""In-process rate limit for hosted control-plane HTTP.

A compromised or noisy client must not be able to create pairing codes or hammer
signed-out routes without bound. Health and ready stay exempt so probes still work.
On any limiter failure the request is denied. The 429 body is a fixed error code.
"""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Protocol

from fastapi import Request
from fastapi.responses import JSONResponse

EXEMPT_PATHS = frozenset({"/health", "/ready"})
DEFAULT_MAX_REQUESTS = 2000
DEFAULT_WINDOW_SECONDS = 60.0


class RateLimiter(Protocol):
    def allow(self, key: str) -> bool: ...


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = monotonic()
        cutoff = now - self._window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


_limiter: RateLimiter = SlidingWindowLimiter(
    max_requests=DEFAULT_MAX_REQUESTS,
    window_seconds=DEFAULT_WINDOW_SECONDS,
)


def install_hosted_rate_limiter(limiter: RateLimiter) -> RateLimiter:
    global _limiter
    previous = _limiter
    _limiter = limiter
    return previous


def check_hosted_rate_limit(request: Request) -> JSONResponse | None:
    if request.url.path in EXEMPT_PATHS:
        return None
    key = request.client.host if request.client is not None else "unknown"
    try:
        allowed = _limiter.allow(key)
    except Exception:
        return _denied()
    if not allowed:
        return _denied()
    return None


def _denied() -> JSONResponse:
    return JSONResponse({"error": "rate_limited"}, status_code=429)
