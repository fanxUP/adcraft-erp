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
from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs, backup, admin, notifications, conversations, acceptances, contracts, framework_contracts, vehicles
# AI module routes
from app.ai.api import ai_anomalies, ai_knowledge, ai_quote, ai_reports, ai_site_photo, ai_payment_ocr

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.SECRET_KEY or settings.SECRET_KEY in ("change_me", "change_me_to_a_random_32_byte_hex_string"):
        logger.warning(
            "SECURITY WARNING: SECRET_KEY is weak or unset. "
            "Generate a strong key with: openssl rand -hex 32"
        )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# WebSocket endpoints
app.add_api_websocket_route("/ws/notifications", notifications.websocket_notifications)
app.add_api_websocket_route("/ws/chat", conversations.websocket_chat)
app.include_router(ai_anomalies.router, prefix="/api/v1")
app.include_router(ai_knowledge.router, prefix="/api/v1")
app.include_router(ai_quote.router, prefix="/api/v1")
app.include_router(ai_reports.router, prefix="/api/v1")
app.include_router(ai_site_photo.router, prefix="/api/v1")
app.include_router(ai_payment_ocr.router, prefix="/api/v1")

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
