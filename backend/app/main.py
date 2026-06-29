from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api import auth, users, customers, products, quotes, orders, tasks, payments, reports, outsource, inventory, operation_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(tasks.design_router, prefix="/api/v1")
app.include_router(tasks.prod_router, prefix="/api/v1")
app.include_router(tasks.inst_router, prefix="/api/v1")
app.include_router(tasks.att_router, prefix="/api/v1")
app.include_router(payments.pay_router, prefix="/api/v1")
app.include_router(payments.stmt_router, prefix="/api/v1")
app.include_router(payments.exp_router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(outsource.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(operation_logs.router, prefix="/api/v1")
