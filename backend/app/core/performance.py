"""
Performance monitoring utilities.

Provides:
  1. SQLAlchemy slow-query logging via engine event listener
  2. FastAPI middleware for per-request timing and logging
"""

import logging
import os
import time
from pathlib import Path

from fastapi import Request, Response
import sqlalchemy.event as sa_event
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

# ── Configuration (overridable via env) ──────────────────────────────────

SLOW_QUERY_MS = int(os.environ.get("PERF_SLOW_QUERY_MS", "200"))
SLOW_API_MS = int(os.environ.get("PERF_SLOW_API_MS", "500"))
PERF_LOG_DIR = os.environ.get("PERF_LOG_DIR", "")


def _log_path() -> str | None:
    """Return a file path for the performance log, or None if not configured."""
    if PERF_LOG_DIR:
        d = Path(PERF_LOG_DIR)
        d.mkdir(parents=True, exist_ok=True)
        return str(d / "performance.log")
    return None


_PERF_LOG = _log_path()


def _write_log(line: str) -> None:
    """Write to the performance log file (if configured) and also log."""
    logger.info(line.rstrip())
    if _PERF_LOG:
        try:
            with open(_PERF_LOG, "a") as f:
                f.write(line)
        except OSError:
            pass


# ── 1. SQLAlchemy slow-query listener ───────────────────────────────────


def install_slow_query_listener(engine) -> None:
    """Attach 'before_cursor_execute' / 'after_cursor_execute' events.

    Works with both sync and async SQLAlchemy engines.
    For async engines, listeners are attached to the underlying sync engine.
    Logs any query that exceeds SLOW_QUERY_MS.
    """

    # Resolve the sync engine (async engines delegate to a sync one)
    sync_engine = getattr(engine, "sync_engine", engine)
    logger.info("Slow-query monitoring installed (threshold=%dms)", SLOW_QUERY_MS)

    # Use a dict to store start time per connection (thread-safe via connection id)
    _start_times: dict[int, float] = {}

    @sa_event.listens_for(sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        _start_times[id(conn)] = time.perf_counter()

    @sa_event.listens_for(sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        start = _start_times.pop(id(conn), None)
        if start is None:
            return
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= SLOW_QUERY_MS:
            # Truncate very long SQL for readability
            sql = (statement[:500] + "...") if len(statement) > 500 else statement
            _write_log(
                "[SLOW-DB] %.0fms | %s\n" % (elapsed_ms, sql)
            )


# ── 2. FastAPI middleware: per-request timing ────────────────────────────


class PerformanceMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that logs request duration for slow endpoints."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip static files and non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Add timing header
        response.headers["X-Response-Time-MS"] = str(round(elapsed_ms, 1))

        if elapsed_ms >= SLOW_API_MS:
            method = request.method
            status = response.status_code
            qs = (f"?{request.url.query}" if request.url.query else "")
            _write_log(
                "[SLOW-API] %.0fms | %s %s%s -> %d\n" % (elapsed_ms, method, path, qs, status)
            )

        return response
