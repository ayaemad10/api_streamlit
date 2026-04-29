"""
api/middleware.py
-----------------
Custom ASGI middleware:
  - LoggingMiddleware: logs every request/response with timing
  - RateLimitMiddleware: simple in-memory rate limiter per IP
"""

import time
import collections
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.logger import get_logger

logger = get_logger("api.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, and response time."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        logger.info(f"→ {request.method} {request.url.path} from {client_ip}")

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(f"Request failed: {exc}", exc_info=True)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] {elapsed_ms:.1f}ms"
        )
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple sliding-window rate limiter per client IP.

    Args:
        max_requests:    Maximum allowed requests per window.
        window_seconds:  Time window in seconds.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # { ip: deque([timestamp, ...]) }
        self._requests: dict[str, collections.deque] = {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/", "/health"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()

        if ip not in self._requests:
            self._requests[ip] = collections.deque()

        window = self._requests[ip]

        # Purge old timestamps outside the current window
        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        window.append(now)
        return await call_next(request)
