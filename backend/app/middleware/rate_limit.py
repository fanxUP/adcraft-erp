"""
Rate-limit middleware for FastAPI.

Integrates the Redis-backed RateLimiter as Starlette middleware
so every request is checked before reaching route handlers.

Client identification (in priority order):
  1. Authenticated user UUID (decoded from JWT in-memory, no DB lookup)
  2. Client IP from X-Forwarded-For
  3. Direct client IP from request.client.host

The RateLimiter instance must be available at app.state.rate_limiter
(populated during the startup lifespan event).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings

if TYPE_CHECKING:
    from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-client rate limits.

    Expects the app to have `app.state.rate_limiter` set during startup.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # ── Skip non-API paths ────────────────────────────────────────
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        # ── Skip WebSocket upgrade requests ───────────────────────────
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # ── Resolve rate limiter ──────────────────────────────────────
        limiter: RateLimiter | None = getattr(request.app.state, "rate_limiter", None)
        if limiter is None:
            # Not yet initialized — allow through
            return await call_next(request)

        # ── Identify client ───────────────────────────────────────────
        client_id = _resolve_client_id(request, limiter)

        # ── Check rate limit ──────────────────────────────────────────
        allowed, retry_after, rule = await limiter.check(
            client_id=client_id,
            path=path,
            method=request.method,
        )

        if not allowed:
            logger.warning(
                "Rate limit exceeded | client=%s path=%s method=%s limit=%d window=%ds",
                client_id, path, request.method, rule.limit, rule.window,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "code": 42900,
                    "message": f"请求过于频繁，请在 {retry_after} 秒后重试",
                    "data": None,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.limit),
                    "X-RateLimit-Window": str(rule.window),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # ── Proceed ───────────────────────────────────────────────────
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rule.limit)
        response.headers["X-RateLimit-Window"] = str(rule.window)
        return response


# ── Module-level helpers ─────────────────────────────────────────────────


def _resolve_client_id(request: Request, limiter: RateLimiter) -> str:
    """Return a stable identifier: user UUID if authenticated, else IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        user_id = _decode_user_id(auth[7:])
        if user_id:
            return f"user:{user_id}"
    return f"ip:{limiter.extract_client_ip(request)}"


def _decode_user_id(token: str) -> str | None:
    """Decode user UUID from JWT without hitting the database."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )
        return payload.get("sub")
    except JWTError:
        return None
