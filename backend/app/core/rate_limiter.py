"""
API Rate Limiter — Redis-based sliding window counter.

Architecture:
  - Uses Redis fixed-window counters with INCR + EXPIRE
  - Key format:  rl:{client_id}:{group}:{window_start}
  - TTL = window_seconds + 5 (grace to avoid race on expiry)

Rules:
  - Each rule matches a path pattern (fnmatch-style: * matches any, ** not needed)
  - First matching rule wins; falls back to default_rule
  - Client ID is either IP or authenticated user UUID

Usage via middleware (app/middleware/rate_limit.py):
  app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

Or direct dependency injection per-route:
  @router.get("/secure")
  async def handler(_=Depends(rate_limiter_dep(limit=5, window=60))):
      ...
"""

from __future__ import annotations

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ── Data classes ───────────────────────────────────────────────────────────


@dataclass
class RateLimitRule:
    """A single rate-limit rule.

    Attributes:
        path_pattern: fnmatch pattern, e.g. "/api/v1/auth/*"
        limit:        max requests in the window
        window:       window in seconds
        group:        route group name for metrics (if None, derived from path)
        method:       HTTP method filter (None = all methods)
    """
    path_pattern: str = "*"
    limit: int = 120
    window: int = 60
    group: Optional[str] = None
    method: Optional[str] = None

    def __post_init__(self) -> None:
        if self.group is None:
            # Derive a short group key from the pattern
            self.group = self.path_pattern.replace("/", "_").replace("*", "wild").strip("_") or "global"


# ── Rate limiter ────────────────────────────────────────────────────────────


class RateLimiter:
    """Redis-backed rate limiter with configurable rules."""

    KEY_PREFIX = "rl"

    def __init__(
        self,
        redis: Redis,
        default_limit: int = 120,
        default_window: int = 60,
    ) -> None:
        self._redis = redis
        self._default_rule = RateLimitRule(
            path_pattern="*",
            limit=default_limit,
            window=default_window,
            group="__default__",
        )
        self._rules: list[RateLimitRule] = []

    # ── Rule registration ──────────────────────────────────────────────

    def add_rule(self, rule: RateLimitRule) -> None:
        """Register a rate-limit rule (most specific first)."""
        self._rules.append(rule)

    def add_rules(self, *rules: RateLimitRule) -> None:
        """Register multiple rules."""
        self._rules.extend(rules)

    # ── Public API ──────────────────────────────────────────────────────

    async def check(self, client_id: str, path: str, method: str) -> tuple[bool, int, RateLimitRule]:
        """Check if a request is allowed.

        Returns:
            (allowed: bool, retry_after_seconds: int, matched_rule: RateLimitRule)
        """
        rule = self._match_rule(path, method)
        window_start = int(time.time() / rule.window) * rule.window
        key = self._key(client_id, rule.group, window_start)

        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, rule.window + 5)
        except Exception:
            logger.warning("Redis rate-limit check failed, allowing request", exc_info=True)
            return True, 0, rule

        if count <= rule.limit:
            return True, 0, rule

        # Rate-limited — compute Retry-After
        retry_after = window_start + rule.window - int(time.time())
        if retry_after < 1:
            retry_after = 1
        return False, retry_after, rule

    async def close(self) -> None:
        """Clean up resources (no-op, Redis connection is managed externally)."""
        pass

    # ── Internals ───────────────────────────────────────────────────────

    def _match_rule(self, path: str, method: str) -> RateLimitRule:
        """Find the first rule matching *path* and *method*."""
        for rule in self._rules:
            if rule.method and rule.method != method:
                continue
            if fnmatch.fnmatch(path, rule.path_pattern):
                return rule
        return self._default_rule

    def _key(self, client_id: str, group: str, window_start: int) -> str:
        """Return the Redis key for a counter."""
        return f"{self.KEY_PREFIX}:{client_id}:{group}:{window_start}"

    @staticmethod
    def extract_client_ip(request) -> str:
        """Extract the real client IP from request headers / client info."""
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host or "unknown"
        return "unknown"


# ── Preset configurations ──────────────────────────────────────────────────


def default_rules() -> list[RateLimitRule]:
    """Return sensible default rules for an ERP backend.

    Order matters — more specific patterns precede general ones.
    """
    return [
        # Auth — strict, prevent brute-force
        RateLimitRule("/api/v1/auth/*",        limit=10,   window=60,   group="auth"),
        RateLimitRule("/api/v1/admin/*",       limit=30,   window=60,   group="admin"),
        # AI endpoints — expensive / external API calls
        RateLimitRule("/api/v1/ai/execute*",   limit=30,   window=60,   group="ai_execute"),
        RateLimitRule("/api/v1/ai/*",          limit=20,   window=60,   group="ai"),
        # File uploads — body-size limited, but still protect
        RateLimitRule("*/upload*",             limit=20,   window=60,   group="upload"),
        RateLimitRule("*/attachments*",        limit=30,   window=60,   group="attachments"),
        # Chat — limit send rate
        RateLimitRule("/api/v1/conversations*", limit=60,  window=60,   group="chat"),
        # CDR quotes — complex calculation
        RateLimitRule("/api/v1/cdr/*",         limit=30,   window=60,   group="cdr"),
        # Static / docs — generous
        RateLimitRule("/api/docs*",            limit=60,   window=60,   group="docs"),
        RateLimitRule("/api/openapi.json",     limit=30,   window=60,   group="docs"),
        # Uploads served as static — no limit (handled at the upload endpoint)
    ]
