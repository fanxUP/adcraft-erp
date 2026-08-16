import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.performance import PerformanceMiddleware, SLOW_QUERY_MS, SLOW_API_MS, install_slow_query_listener
from app.middleware.rate_limit import RateLimitMiddleware
from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs, backup, admin, notifications, conversations, acceptances, contracts, framework_contracts, vehicles, vehicle_agent, vehicle_dashboard, aerial, ai_execute, ai_models, ai_providers, ai_prompts, ai_requests, ai_routes, employees, attendance, departments, salaries, salary_rules, employment_histories, leaves
from app.api import cdr_quotes
# AI module routes
from app.ai.api import ai_anomalies, ai_knowledge, ai_quote, ai_reports, ai_site_photo, ai_payment_ocr
from app.ai_assistant.router import router as ai_assistant_router

logger = logging.getLogger(__name__)


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
        from app.core.redis import get_redis
        from app.core.rate_limiter import RateLimiter, default_rules
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
    yield


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
    return JSONResponse(status_code=400, content={"code": 40001, "message": str(exc), "data": None})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code * 100, "message": exc.detail, "data": None})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    except Exception:
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
