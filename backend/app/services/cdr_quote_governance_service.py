"""CDR 智能报价——业务服务层。"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.services.price_engine import (
    PriceEngine, CalculateRequest, CalculateResult,
    ProductInfo, MaterialInfo, ProcessInfo, CustomerAgreement,
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

    # ── 规则集 ──

    async def list_rule_sets(self) -> list[dict]:
        rule_sets = await self.repo.list_rule_sets()
        return [{
            "id": str(rs.id),
            "code": rs.code,
            "name": rs.name,
            "version": rs.version,
            "status": rs.status,
            "effective_from": rs.effective_from,
            "effective_to": rs.effective_to,
            "description": rs.description,
        } for rs in rule_sets]

    async def create_rule_set(self, data: dict, published_by: UUID) -> dict:
        rules_data = data.pop("rules", [])
        rs = await self.repo.create_rule_set({
            "code": data["code"],
            "name": data["name"],
            "effective_from": data.get("effective_from"),
            "effective_to": data.get("effective_to"),
            "description": data.get("description"),
            "published_by": published_by,
        })
        for rule_data in rules_data:
            from app.models.cdr_quote import CdrPriceRule
            rule = CdrPriceRule(
                rule_set_id=rs.id,
                code=rule_data["code"],
                name=rule_data["name"],
                priority=rule_data.get("priority", 0),
                conditions_json=rule_data.get("conditions_json", {}),
                actions_json=rule_data.get("actions_json", {}),
                conflict_policy=rule_data.get("conflict_policy", "higher_priority_wins"),
            )
            self.db.add(rule)
        await self.db.flush()
        return {"id": str(rs.id), "code": rs.code, "name": rs.name}

    # ── 客户协议价 ──

    async def list_customer_agreements(self, customer_id: UUID | None = None) -> list[dict]:
        agreements = await self.repo.list_customer_agreements(customer_id)
        return [{
            "id": str(ca.id),
            "customer_id": str(ca.customer_id),
            "product_id": str(ca.product_id) if ca.product_id else None,
            "pricing_method": ca.pricing_method,
            "price_value": str(ca.price_value),
            "minimum_charge": str(ca.minimum_charge),
            "discount_rate": str(ca.discount_rate),
            "effective_from": ca.effective_from,
            "effective_to": ca.effective_to,
            "remark": ca.remark,
        } for ca in agreements]

    async def create_customer_agreement(self, data: dict, approved_by: UUID) -> dict:
        ca = await self.repo.create_customer_agreement({
            "customer_id": UUID(data["customer_id"]),
            "product_id": UUID(data["product_id"]) if data.get("product_id") else None,
            "material_id": UUID(data["material_id"]) if data.get("material_id") else None,
            "process_id": UUID(data["process_id"]) if data.get("process_id") else None,
            "pricing_method": data["pricing_method"],
            "price_value": Decimal(str(data["price_value"])),
            "minimum_charge": Decimal(str(data.get("minimum_charge", 0))),
            "discount_rate": Decimal(str(data.get("discount_rate", 1))),
            "effective_from": data["effective_from"],
            "effective_to": data.get("effective_to"),
            "remark": data.get("remark"),
            "approved_by": approved_by,
        })
        return {"id": str(ca.id), "customer_id": str(ca.customer_id)}

    async def update_customer_agreement(self, agreement_id: UUID, data: dict) -> dict:
        """Update an existing customer agreement."""
        ca = await self.repo.update_customer_agreement(agreement_id, {
            "product_id": UUID(data["product_id"]) if data.get("product_id") else None,
            "material_id": UUID(data["material_id"]) if data.get("material_id") else None,
            "process_id": UUID(data["process_id"]) if data.get("process_id") else None,
            "pricing_method": data.get("pricing_method"),
            "price_value": Decimal(str(data["price_value"])) if data.get("price_value") is not None else None,
            "minimum_charge": Decimal(str(data.get("minimum_charge", 0))),
            "discount_rate": Decimal(str(data.get("discount_rate", 1))),
            "effective_from": data.get("effective_from"),
            "effective_to": data.get("effective_to"),
            "remark": data.get("remark"),
        })
        if not ca:
            raise ValueError("协议价记录不存在")
        return {"id": str(ca.id), "customer_id": str(ca.customer_id)}

    async def delete_customer_agreement(self, agreement_id: UUID) -> bool:
        """Delete a customer agreement."""
        return await self.repo.delete_customer_agreement(agreement_id)

    async def batch_customer_agreements(self, data: dict) -> dict:
        """Batch create/update customer agreements by customer_type/level or customer_ids."""
        from sqlalchemy import select
        from app.models.customer import Customer

        customer_type = data.get("customer_type")
        level = data.get("level")
        customer_ids = data.get("customer_ids")
        product_ids = data.get("product_ids", [])
        pricing_method = data.get("pricing_method", "quantity")
        price_value = Decimal(str(data.get("price_value", 0)))
        minimum_charge = Decimal(str(data.get("minimum_charge", 0)))
        discount_rate = Decimal(str(data.get("discount_rate", 1)))
        effective_from = data.get("effective_from", "")
        effective_to = data.get("effective_to")
        overwrite = data.get("overwrite", True)

        if customer_ids:
            matched_ids = [UUID(cid) for cid in customer_ids]
        else:
            q = select(Customer.id).where(Customer.deleted_at.is_(None))
            if customer_type:
                q = q.where(Customer.customer_type == customer_type)
            if level:
                q = q.where(Customer.level == level)
            result = await self.db.execute(q)
            matched_ids = [row[0] for row in result.all()]

        if not matched_ids:
            return {"created": 0, "updated": 0, "skipped": 0}

        if not product_ids:
            from app.models.product import Product
            result = await self.db.execute(select(Product.id).where(Product.is_active == True))
            product_ids = [str(row[0]) for row in result.all()]

        created = 0
        updated = 0
        skipped = 0

        for cid in matched_ids:
            for pid in product_ids:
                pid_uuid = UUID(pid)
                existing = await self.repo.get_customer_agreement(cid, pid_uuid)
                if existing:
                    if overwrite:
                        await self.repo.update_customer_agreement(existing.id, {
                            "product_id": pid_uuid,
                            "price_value": price_value,
                            "minimum_charge": minimum_charge,
                            "discount_rate": discount_rate,
                            "pricing_method": pricing_method,
                            "effective_from": effective_from,
                            "effective_to": effective_to,
                        })
                        updated += 1
                    else:
                        skipped += 1
                else:
                    await self.repo.create_customer_agreement({
                        "customer_id": cid,
                        "product_id": pid_uuid,
                        "pricing_method": pricing_method,
                        "price_value": price_value,
                        "minimum_charge": minimum_charge,
                        "discount_rate": discount_rate,
                        "effective_from": effective_from or date.today().isoformat(),
                        "effective_to": effective_to,
                    })
                    created += 1

        return {"created": created, "updated": updated, "skipped": skipped}
