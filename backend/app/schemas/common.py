from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None) -> dict:
    return {"code": 0, "message": "success", "data": data}


def success_paginated(items: list, total: int, page: int, page_size: int) -> dict:
    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


def error(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}
