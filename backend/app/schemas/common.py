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


from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import model_validator


class CoercedModel(BaseModel):
    """Base model that coerces UUID/datetime/Decimal when validating from SQLAlchemy objects."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_sa_types(cls, data):
        if isinstance(data, dict):
            return data
        result = {}
        for name in cls.model_fields:
            try:
                val = getattr(data, name)
            except AttributeError:
                continue
            if isinstance(val, UUID):
                result[name] = str(val)
            elif isinstance(val, datetime):
                result[name] = val.isoformat()
            elif isinstance(val, Decimal):
                result[name] = float(val)
            else:
                result[name] = val
        return result

    model_config = {"from_attributes": True}
