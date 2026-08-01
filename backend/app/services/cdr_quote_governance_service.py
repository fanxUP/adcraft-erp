"""CDR 智能报价——业务服务层。"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.services.price_engine import (
    PriceEngine, CalculateRequest, CalculateResult,
    ProductInfo, MaterialInfo, ProcessInfo,
)
from app.models.product import Product, Material, Process

from app.services.cdr_quote_base_service import CdrQuoteServiceBase


class CdrQuoteGovernanceService(CdrQuoteServiceBase):
    # ── 审批 ──

    async def request_approval(self, quote_id: UUID, data: dict, requested_by: UUID) -> dict:
        """请求审批。"""
        version = await self.repo.get_latest_version(quote_id)
        if not version:
            raise ValueError("报价没有版本")

        approval = await self.repo.create_approval({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "approval_type": data.get("approval_type", "price_override"),
            "requested_by": requested_by,
            "status": "pending",
            "reason": data.get("reason"),
        })

        if version.status == "draft":
            await self.repo.update_version_status(version.id, "review")

        await self.repo.create_audit_log({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "actor_id": requested_by,
            "action": "approval.requested",
            "after_json": {"approval_type": data.get("approval_type")},
        })

        return {
            "id": str(approval.id),
            "status": "pending",
            "approval_type": approval.approval_type,
            "reason": approval.reason,
        }

    async def approve(self, approval_id: UUID, approver_id: UUID, comment: str | None = None) -> dict:
        """批准报价。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        r = await self.db.execute(select(QuoteApproval).where(QuoteApproval.id == approval_id))
        approval = r.scalar_one_or_none()
        if not approval:
            raise ValueError("审批记录不存在")

        await self.repo.update_approval(approval_id, {
            "status": "approved",
            "approver_id": approver_id,
            "decision_comment": comment,
            "decided_at": datetime.utcnow(),
        })
        if approval.quote_version_id:
            await self.repo.update_version_status(approval.quote_version_id, "approved")

        await self.repo.create_audit_log({
            "quote_id": approval.quote_id,
            "quote_version_id": approval.quote_version_id,
            "actor_id": approver_id,
            "action": "approval.approved",
            "after_json": {"comment": comment},
        })

        return {"status": "approved"}

    async def reject(self, approval_id: UUID, approver_id: UUID, comment: str | None = None) -> dict:
        """驳回报价。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        r = await self.db.execute(select(QuoteApproval).where(QuoteApproval.id == approval_id))
        approval = r.scalar_one_or_none()
        if not approval:
            raise ValueError("审批记录不存在")

        await self.repo.update_approval(approval_id, {
            "status": "rejected",
            "approver_id": approver_id,
            "decision_comment": comment,
            "decided_at": datetime.utcnow(),
        })

        await self.repo.create_audit_log({
            "quote_id": approval.quote_id,
            "quote_version_id": approval.quote_version_id,
            "actor_id": approver_id,
            "action": "approval.rejected",
            "after_json": {"comment": comment},
        })

        return {"status": "rejected"}

    async def list_approvals(self, quote_id: UUID) -> list[dict]:
        """获取报价审批记录列表。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        from app.models.user import User
        r = await self.db.execute(
            select(QuoteApproval)
            .where(QuoteApproval.quote_id == quote_id)
            .order_by(QuoteApproval.created_at.desc())
        )
        approvals = r.scalars().all()
        return [{
            "id": str(a.id),
            "quote_id": str(a.quote_id),
            "quote_version_id": str(a.quote_version_id) if a.quote_version_id else None,
            "approval_type": a.approval_type,
            "status": a.status,
            "reason": a.reason,
            "decision_comment": a.decision_comment,
            "requested_by": str(a.requested_by) if a.requested_by else None,
            "approver_id": str(a.approver_id) if a.approver_id else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
        } for a in approvals]
