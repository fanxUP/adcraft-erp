"""CDR 智能报价——API 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission, PERM_CDR_QUOTE_READ, PERM_CDR_QUOTE_CREATE, PERM_CDR_QUOTE_APPROVE, PERM_CDR_QUOTE_CONVERT
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.services.cdr_quote_service import CdrQuoteService

router = APIRouter(prefix="/cdr", tags=["CDR 智能报价"])


# ── 报价列表 / 详情 ─────────────────────────────────────────────

@router.get("/quotes")
async def list_cdr_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """CDR 智能报价列表。"""
    service = CdrQuoteService(db)
    quotes, total = await service.list_quotes(page, page_size, status, keyword)
    return success_paginated(quotes, total, page, page_size)


@router.get("/quotes/{quote_id}")
async def get_cdr_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """CDR 智能报价详情。"""
    service = CdrQuoteService(db)
    quote = await service.get_quote(quote_id)
    if not quote:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="报价不存在")
    return success(quote)


# ── 报价试算 ────────────────────────────────────────────────────

@router.post("/pricing/calculate")
async def calculate_price(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """报价试算（不保存，返回规则执行明细）。"""
    service = CdrQuoteService(db)
    result = await service.calculate(data)
    return success(result)


# ── 报价版本 ────────────────────────────────────────────────────

@router.post("/quotes/{quote_id}/versions")
async def create_version(
    quote_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """为报价创建新版本（含明细行，自动试算）。"""
    service = CdrQuoteService(db)
    version = await service.create_quote_version(quote_id, data, current_user.id)
    return success(version)


@router.get("/quotes/{quote_id}/versions/latest")
async def get_latest_version(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价最新版本。"""
    service = CdrQuoteService(db)
    version = await service.get_latest_version(quote_id)
    return success(version)


@router.get("/quotes/{quote_id}/versions")
async def list_versions(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价版本历史。"""
    service = CdrQuoteService(db)
    versions = await service.list_versions(quote_id)
    return success(versions)


# ── 审批 ────────────────────────────────────────────────────────

@router.get("/quotes/{quote_id}/approvals")
async def list_cdr_approvals(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价审批记录列表。"""
    service = CdrQuoteService(db)
    approvals = await service.list_approvals(quote_id)
    return success(approvals)


@router.post("/quotes/{quote_id}/approvals")
async def request_approval(
    quote_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """请求报价审批。"""
    service = CdrQuoteService(db)
    result = await service.request_approval(quote_id, data, current_user.id)
    return success(result)


@router.post("/approvals/{approval_id}/approve")
async def approve_quote(
    approval_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_APPROVE)),
):
    """批准报价。"""
    service = CdrQuoteService(db)
    result = await service.approve(approval_id, current_user.id, data.get("comment") if data else None)
    return success(result)


@router.post("/approvals/{approval_id}/reject")
async def reject_quote(
    approval_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_APPROVE)),
):
    """驳回报价。"""
    service = CdrQuoteService(db)
    result = await service.reject(approval_id, current_user.id, data.get("comment") if data else None)
    return success(result)


# ── 规则集 ──────────────────────────────────────────────────────

@router.get("/rule-sets")
async def list_rule_sets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取定价规则集列表。"""
    service = CdrQuoteService(db)
    rule_sets = await service.list_rule_sets()
    return success(rule_sets)


@router.post("/rule-sets")
async def create_rule_set(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建定价规则集（含规则）。"""
    service = CdrQuoteService(db)
    result = await service.create_rule_set(data, current_user.id)
    return success(result)


# ── 客户协议价 ──────────────────────────────────────────────────

@router.get("/customer-agreements")
async def list_customer_agreements(
    customer_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取客户协议价列表。"""
    service = CdrQuoteService(db)
    agreements = await service.list_customer_agreements(customer_id)
    return success(agreements)


@router.post("/customer-agreements")
async def create_customer_agreement(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建客户协议价。"""
    service = CdrQuoteService(db)
    result = await service.create_customer_agreement(data, current_user.id)
    return success(result)


# ── 审计日志 ────────────────────────────────────────────────────

@router.get("/quotes/{quote_id}/audit-logs")
async def list_audit_logs(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取报价审计日志。"""
    service = CdrQuoteService(db)
    logs = await service.list_audit_logs(quote_id)
    return success(logs)


# ── 转订单 ────────────────────────────────────────────────────

@router.post("/quotes/{quote_id}/convert-to-order")
async def convert_to_order(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CONVERT)),
):
    """将CDR智能报价转为销售订单（创建新订单，保留报价历史）。"""
    service = CdrQuoteService(db)
    result = await service.convert_to_order(quote_id, current_user.id)
    return success(result)
