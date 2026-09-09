from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

UiTone = Literal["brand", "success", "warning", "danger", "info", "neutral"]


class ApiMeta(BaseModel):
    """Transport metadata that is safe for the UI to display or log."""

    request_id: str | None = None
    timestamp: str | None = None


class ApiFieldError(BaseModel):
    """One validation error in the stable API error payload."""

    loc: list[str | int] = Field(default_factory=list)
    msg: str
    type: str | None = None


class StatusView(BaseModel):
    """Canonical status semantics consumed by all UI surfaces."""

    code: str
    label: str
    tone: UiTone = "neutral"
    terminal: bool = False


class ActionCapability(BaseModel):
    """Object-state capability; backend authorization still remains final."""

    allowed: bool
    disabled_reason: str | None = None
    requires_confirmation: bool = False


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None
    meta: ApiMeta | None = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None, *, meta: dict | ApiMeta | None = None) -> dict:
    payload = {"code": 0, "message": "success", "data": data}
    if meta is not None:
        payload["meta"] = meta.model_dump(mode="json") if isinstance(meta, ApiMeta) else meta
    return payload


def success_paginated(
    items: list,
    total: int,
    page: int,
    page_size: int,
    *,
    meta: dict | ApiMeta | None = None,
) -> dict:
    return success(
        {"items": items, "total": total, "page": page, "page_size": page_size},
        meta=meta,
    )


def error(
    code: int,
    message: str,
    *,
    data: Any = None,
    meta: dict | ApiMeta | None = None,
) -> dict:
    payload = {"code": code, "message": message, "data": data}
    if meta is not None:
        payload["meta"] = meta.model_dump(mode="json") if isinstance(meta, ApiMeta) else meta
    return payload


from uuid import UUID
from datetime import date, datetime
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
            elif isinstance(val, date):
                result[name] = val.isoformat()
            else:
                result[name] = val
        return result

    model_config = {"from_attributes": True}
