"""Circuit breaker for AI provider calls.

States:
  CLOSED    — normal operation, requests pass through
  OPEN      — failures exceed threshold, requests are rejected
  HALF_OPEN — after cooldown, probe requests are allowed

Thread-safe via asyncio lock.
"""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Request rejected because circuit breaker is OPEN."""


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    rolling_window_seconds: int = 120
    open_duration_seconds: int = 60
    half_open_probe_count: int = 2


class CircuitBreaker:
    """Per-provider circuit breaker."""

    def __init__(self, provider_id: str, config: Optional[CircuitBreakerConfig] = None):
        self.provider_id = provider_id
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self._failures: deque[float] = deque(maxlen=100)
        self._open_since: float = 0.0
        self._half_open_attempts = 0
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """Execute a function through the circuit breaker.

        Raises CircuitBreakerError if circuit is OPEN (and not ready for probe).
        Raises the original exception from func on failure.
        """
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self._open_since >= self.config.open_duration_seconds:
                async with self._lock:
                    if self.state == CircuitState.OPEN:
                        self.state = CircuitState.HALF_OPEN
                        self._half_open_attempts = 0
                        logger.info("Circuit breaker %s: OPEN → HALF_OPEN (cooldown elapsed)", self.provider_id)
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker OPEN for {self.provider_id}, "
                    f"retry in {self.config.open_duration_seconds - (time.monotonic() - self._open_since):.0f}s"
                )

        if self.state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_attempts >= self.config.half_open_probe_count:
                    raise CircuitBreakerError(
                        f"Circuit breaker HALF_OPEN for {self.provider_id}, "
                        f"max probe count ({self.config.half_open_probe_count}) reached"
                    )
                self._half_open_attempts += 1

        try:
            result = await func(*args, **kwargs)
            # Success — reset if half-open
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self._reset()
                    logger.info("Circuit breaker %s: HALF_OPEN → CLOSED (probe succeeded)", self.provider_id)
            return result
        except CircuitBreakerError:
            raise
        except Exception as exc:
            await self._record_failure(exc)
            raise

    async def _record_failure(self, exc: Exception) -> None:
        now = time.monotonic()
        async with self._lock:
            # Prune old failures outside the window
            cutoff = now - self.config.rolling_window_seconds
            while self._failures and self._failures[0] < cutoff:
                self._failures.popleft()

            self._failures.append(now)

            if len(self._failures) >= self.config.failure_threshold:
                if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                    self.state = CircuitState.OPEN
                    self._open_since = now
                    logger.warning(
                        "Circuit breaker %s: %s → OPEN (%d failures in %ds)",
                        self.provider_id,
                        self.state.value,
                        len(self._failures),
                        self.config.rolling_window_seconds,
                    )

    def _reset(self) -> None:
        self.state = CircuitState.CLOSED
        self._failures.clear()
        self._open_since = 0.0
        self._half_open_attempts = 0

    @property
    def is_available(self) -> bool:
        """Quick check without acquiring lock (best-effort)."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            return time.monotonic() - self._open_since >= self.config.open_duration_seconds
        return self._half_open_attempts < self.config.half_open_probe_count


class CircuitBreakerRegistry:
    """Global registry of circuit breakers keyed by provider_id."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_config(self, circuit_breaker_json: Optional[dict] = None) -> CircuitBreakerConfig:
        """Build config from JSON dict, falling back to defaults."""
        if not circuit_breaker_json:
            return CircuitBreakerConfig()
        return CircuitBreakerConfig(
            failure_threshold=circuit_breaker_json.get("failure_threshold", 5),
            rolling_window_seconds=circuit_breaker_json.get("rolling_window_seconds", 120),
            open_duration_seconds=circuit_breaker_json.get("open_duration_seconds", 60),
            half_open_probe_count=circuit_breaker_json.get("half_open_probe_count", 2),
        )

    async def get_or_create(self, provider_id: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        async with self._lock:
            if provider_id not in self._breakers:
                self._breakers[provider_id] = CircuitBreaker(provider_id, config)
            return self._breakers[provider_id]


# Global instance
circuit_breaker_registry = CircuitBreakerRegistry()
