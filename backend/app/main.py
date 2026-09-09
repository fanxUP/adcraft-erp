import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

# AI module routes
from app.ai.api import (
    ai_anomalies,
    ai_knowledge,
    ai_payment_ocr,
    ai_quote,
    ai_reports,
    ai_site_photo,
)
from app.ai_assistant.router import router as ai_assistant_router
from app.api import (
    acceptances,
    admin,
    aerial,
    ai_execute,
    ai_models,
    ai_prompts,
    ai_providers,
    ai_requests,
    ai_routes,
    attendance,
    auth,
    backup,
    cdr_quotes,
    contracts,
    conversations,
    customers,
    departments,
    employees,
    employment_histories,
    framework_contracts,
    inventory,
    leaves,
    notifications,
    operation_logs,
    orders,
    outsource,
    payments,
    products,
    quotes,
    reports,
    salaries,
    salary_rules,
    tasks,
    users,
    vehicle_agent,
    vehicle_dashboard,
    vehicles,
)
from app.core.config import settings
from app.core.performance import (
    SLOW_API_MS,
    SLOW_QUERY_MS,
    PerformanceMiddleware,
    install_slow_query_listener,
)
from app.middleware.rate_limit import RateLimitMiddleware
from app.schemas.common import error

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _request_id(request: Request) -> str:
    """Return a bounded correlation id without trusting arbitrary header text."""
    candidate = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
    if 1 <= len(candidate) <= 128 and all(
        char.isalnum() or char in "-_" for char in candidate
    ):
        return candidate
    return uuid4().hex


def _error_meta(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.SECRET_KEY or settings.SECRET_KEY in ("change_me", "change_me_to_a_random_32_byte_hex_string"):
        message = "SECRET_KEY 未设置或过弱，请使用 openssl rand -hex 32 生成"
        if settings.APP_ENV.lower() in {"production", "prod"}:
            raise RuntimeError(message)
        logger.warning("SECURITY WARNING: %s", message)
    # Performance monitoring: install slow-query listener on the database engine
    from app.core.database import engine
    install_slow_query_listener(engine)
    logger.info("Performance monitoring active (slow-query %dms, slow-api %dms)",
                 SLOW_QUERY_MS, SLOW_API_MS)
    # Rate limiting: Redis-backed，覆盖 auth/ai/upload 等关键路径防爆破（测试环境跳过，避免干扰用例）
    if settings.APP_ENV.lower() != "test":
        from app.core.rate_limiter import RateLimiter, default_rules
        from app.core.redis import get_redis
        try:
            _rl_redis = await get_redis()
            _limiter = RateLimiter(_rl_redis)
            _limiter.add_rules(*default_rules())
            app.state.rate_limiter = _limiter
            logger.info("Rate limiter active (Redis-backed)")
        except Exception:
            logger.warning("Rate limiter unavailable (Redis down?), continuing without it", exc_info=True)
    if (
        settings.AI_BUSINESS_RULE_SYNC_ON_STARTUP
        and settings.APP_ENV.lower() != "test"
    ):
        from app.ai_assistant.business_rules.startup import (
            synchronize_business_rules_at_startup,
        )

        try:
            sync_result = await synchronize_business_rules_at_startup()
            logger.info(
                "AI business rules synchronized: added=%d updated=%d retired=%d",
                sync_result["added_count"],
                sync_result["updated_count"],
                sync_result["retired_count"],
            )
        except Exception:
            if settings.APP_ENV.lower() in {"production", "prod"}:
                raise
            logger.exception(
                "AI business-rule startup sync failed; AI will use source rules"
            )
    overdue_notification_task = None
    if settings.APP_ENV.lower() != "test":
        from app.services.task_overdue_notification_service import (
            run_overdue_notification_loop,
        )

        overdue_notification_task = asyncio.create_task(
            run_overdue_notification_loop(),
            name="overdue-task-notifications",
        )
        app.state.overdue_notification_task = overdue_notification_task
        logger.info("Overdue task notification scheduler active (15-minute interval)")

    try:
        yield
    finally:
        if overdue_notification_task is not None:
            overdue_notification_task.cancel()
            try:
                await overdue_notification_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    # 生产环境经公网隧道可达，关闭 /api/docs 与 /api/openapi.json 避免路由面暴露（2026-08-16 安全加固）
    docs_url="/api/docs" if settings.APP_ENV.lower() != "production" else None,
    openapi_url="/api/openapi.json" if settings.APP_ENV.lower() != "production" else None,
    lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=error(40001, str(exc), meta=_error_meta(request)),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    fields = [
        {
            "loc": [str(part) for part in item.get("loc", ())],
            "msg": str(item.get("msg", "请求参数错误")),
            "type": item.get("type"),
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error(
            42200,
            "请求参数错误",
            data={"fields": fields},
            meta=_error_meta(request),
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    message = detail if isinstance(detail, str) else "请求失败"
    explicit_code = None
    if exc.headers:
        raw_code = exc.headers.get("X-Error-Code")
        if raw_code and raw_code.isdigit():
            explicit_code = int(raw_code)
    code = explicit_code or exc.status_code * 100
    if exc.status_code == 403 and message == "请先修改初始密码":
        code = 40300
    return JSONResponse(
        status_code=exc.status_code,
        content=error(code, message, meta=_error_meta(request)),
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled API error request_id=%s",
        getattr(request.state, "request_id", None),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=error(50000, "服务器内部错误，请稍后重试", meta=_error_meta(request)),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = _request_id(request)
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request.state.request_id
    return response

# 全局限流中间件（Redis 未就绪时自动放行，规则见 core/rate_limiter.default_rules）
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.APP_ENV.lower() in {"production", "prod"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# Performance monitoring: logs response times and adds X-Response-Time-MS header
app.add_middleware(PerformanceMiddleware)


@app.get("/api/v1/health")
async def health_check():
    """健康检查：nginx /health 与外部监控使用，探测数据库连通性。

    DB 可达返回 200，不可达返回 503，便于负载均衡/监控探针区分。
    """
    from sqlalchemy import text

    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 - health checks convert any database failure into HTTP 503
        db_status = "error"
    status_code = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "code": 0 if db_status == "ok" else 50000,
            "message": "ok" if db_status == "ok" else "database unreachable",
            "data": {"status": "ok" if db_status == "ok" else "error", "database": db_status},
        },
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(products.cat_router, prefix="/api/v1")
app.include_router(products.mat_router, prefix="/api/v1")
app.include_router(products.proc_router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(contracts.router, prefix="/api/v1")
app.include_router(framework_contracts.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(salaries.router, prefix="/api/v1")

app.include_router(salary_rules.router, prefix="/api/v1")
app.include_router(employment_histories.router, prefix="/api/v1")
app.include_router(leaves.router, prefix="/api/v1")
app.include_router(tasks.design_router, prefix="/api/v1")
app.include_router(tasks.prod_router, prefix="/api/v1")
app.include_router(tasks.inst_router, prefix="/api/v1")
app.include_router(tasks.queue_router, prefix="/api/v1")
app.include_router(tasks.att_router, prefix="/api/v1")
app.include_router(payments.pay_router, prefix="/api/v1")
app.include_router(payments.stmt_router, prefix="/api/v1")
app.include_router(payments.exp_router, prefix="/api/v1")
app.include_router(payments.cost_router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(outsource.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(operation_logs.router, prefix="/api/v1")
app.include_router(backup.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(acceptances.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(vehicles.driver_router, prefix="/api/v1")
app.include_router(vehicles.request_router, prefix="/api/v1")
app.include_router(vehicles.dispatch_router, prefix="/api/v1")
app.include_router(vehicles.trip_router, prefix="/api/v1")
app.include_router(vehicles.fuel_router, prefix="/api/v1")
app.include_router(vehicles.maintenance_router, prefix="/api/v1")
app.include_router(vehicles.cost_router, prefix="/api/v1")
app.include_router(vehicles.certificate_router, prefix="/api/v1")
app.include_router(vehicles.incident_router, prefix="/api/v1")
app.include_router(vehicles.report_router, prefix="/api/v1")
app.include_router(vehicle_agent.router, prefix="/api/v1")
app.include_router(vehicle_dashboard.router, prefix="/api/v1")

# Aerial work platform
app.include_router(aerial.router, prefix="/api/v1")
app.include_router(aerial.personnel_router, prefix="/api/v1")
app.include_router(aerial.ledger_router, prefix="/api/v1")
app.include_router(aerial.expense_router, prefix="/api/v1")
app.include_router(aerial.wage_router, prefix="/api/v1")
app.include_router(aerial.cost_router, prefix="/api/v1")
app.include_router(aerial.safety_router, prefix="/api/v1")
app.include_router(aerial.attachment_router, prefix="/api/v1")
app.include_router(aerial.dashboard_router, prefix="/api/v1")
app.include_router(aerial.report_router, prefix="/api/v1")
app.include_router(aerial.agent_router, prefix="/api/v1")
app.include_router(aerial.attendance_router, prefix="/api/v1")

# WebSocket endpoints
app.add_api_websocket_route("/ws/notifications", notifications.websocket_notifications)
app.add_api_websocket_route("/ws/chat", conversations.websocket_chat)
app.include_router(ai_anomalies.router, prefix="/api/v1")
app.include_router(ai_knowledge.router, prefix="/api/v1")
app.include_router(ai_quote.router, prefix="/api/v1")
app.include_router(ai_reports.router, prefix="/api/v1")
app.include_router(ai_site_photo.router, prefix="/api/v1")
app.include_router(ai_payment_ocr.router, prefix="/api/v1")
# AI infrastructure (model management, providers, execution)
app.include_router(ai_execute.router, prefix="/api/v1")
app.include_router(ai_models.router, prefix="/api/v1")
app.include_router(ai_providers.router, prefix="/api/v1")
app.include_router(ai_prompts.router, prefix="/api/v1")
app.include_router(ai_requests.router, prefix="/api/v1")
app.include_router(ai_routes.router, prefix="/api/v1")

# CDR 智能报价
app.include_router(cdr_quotes.router, prefix="/api/v1")
app.include_router(ai_assistant_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Static file serving (frontend SPA + uploads)
# When running under PyInstaller, paths are resolved relative to the executable.
# ---------------------------------------------------------------------------

# Determine the base directory
if getattr(sys, "frozen", False):
    # PyInstaller --onedir: sys._MEIPASS points to the _internal directory
    _EXE_DIR = Path(sys.executable).parent if hasattr(sys, "executable") else Path.cwd()
else:
    _EXE_DIR = Path(__file__).resolve().parent.parent.parent

FRONTEND_DIR = os.environ.get("FRONTEND_DIR", str(_EXE_DIR / "frontend"))
# Use the same LOCAL_UPLOAD_DIR that upload APIs (tasks.py, etc.) use via settings
UPLOAD_DIR = os.environ.get("LOCAL_UPLOAD_DIR") or os.path.abspath(settings.LOCAL_UPLOAD_DIR)

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# GZip compression for text-based responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount uploads BEFORE frontend — more specific paths must come first
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount the Vue SPA frontend as catch-all (html=True enables SPA fallback)
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
