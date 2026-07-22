from datetime import date, datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contract_repo import ContractRepository
from app.services.number_generator import generate_contract_no


# 状态流转映射
CONTRACT_TRANSITIONS = {
    "draft": ["active", "completed"],
    "active": ["draft", "completed"],
    "completed": ["draft"],
}


class ContractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ContractRepository(db)

    async def _calc_paid_amount(self, contract_id: UUID) -> float:
        """计算合同已收金额 = 关联单据的收款总和（不含已作废）"""
        from sqlalchemy import select, func
        from app.models.payment import Payment
        from app.models.contract import ContractDocument

        result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .join(ContractDocument, ContractDocument.document_id == Payment.document_id)
            .where(
                ContractDocument.contract_id == contract_id,
                Payment.is_voided == False,
            )
        )
        return float(result.scalar())

    async def _batch_paid_amounts(self, contract_ids: list[UUID]) -> dict[UUID, float]:
        """批量计算多个合同的已收金额"""
        if not contract_ids:
            return {}
        from sqlalchemy import select, func
        from app.models.payment import Payment
        from app.models.contract import ContractDocument

        result = await self.db.execute(
            select(
                ContractDocument.contract_id,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .select_from(Payment)
            .join(ContractDocument, ContractDocument.document_id == Payment.document_id)
            .where(
                ContractDocument.contract_id.in_(contract_ids),
                Payment.is_voided == False,
            )
            .group_by(ContractDocument.contract_id)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    async def _calc_framework_total(self, contract_id: UUID) -> float:
        """计算框架合同的金额 = 所有子项目金额之和"""
        from sqlalchemy import select, func
        from app.models.framework_contract import FrameworkContractProject

        result = await self.db.execute(
            select(func.coalesce(func.sum(FrameworkContractProject.project_amount), 0))
            .where(
                FrameworkContractProject.contract_id == contract_id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )
        return float(result.scalar())

    async def _batch_framework_totals(self, contract_ids: list[UUID]) -> dict[UUID, float]:
        """批量计算多个框架合同的金额"""
        if not contract_ids:
            return {}
        from sqlalchemy import select, func
        from app.models.framework_contract import FrameworkContractProject

        result = await self.db.execute(
            select(
                FrameworkContractProject.contract_id,
                func.coalesce(func.sum(FrameworkContractProject.project_amount), 0),
            )
            .where(
                FrameworkContractProject.contract_id.in_(contract_ids),
                FrameworkContractProject.deleted_at.is_(None),
            )
            .group_by(FrameworkContractProject.contract_id)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    async def _auto_complete_if_paid(self, contracts: list) -> None:
        """已收金额>=合同金额时自动将状态改为已完成"""
        cids = [c.id for c in contracts]
        if not cids:
            return
        paid_map = await self._batch_paid_amounts(cids)
        changed = False
        for c in contracts:
            paid = paid_map.get(c.id, 0.0)
            if paid >= float(c.total_amount) and float(c.total_amount) > 0 and c.status not in ("completed",):
                c.status = "completed"
                changed = True
        if changed:
            await self.db.flush()

    def _to_response(self, contract) -> dict:
        # 从关联单据提取部门和来源
        docs = contract.documents or []
        departments = list({d.department for d in docs if d.department})
        department = "、".join(departments) if departments else ""
        doc_types = {d.doc_type for d in docs}
        if "order" in doc_types and "quote" in doc_types:
            source = "订单+报价"
        elif "order" in doc_types:
            source = "订单"
        elif "quote" in doc_types:
            source = "报价"
        else:
            source = ""
        return {
            "id": str(contract.id),
            "contract_no": contract.contract_no,
            "customer_name": contract.customer_name,
            "project_name": contract.project_name,
            "total_amount": float(contract.total_amount) if contract.total_amount else 0,
            "paid_amount": float(contract.paid_amount) if contract.paid_amount else 0,
            "unpaid_amount": float(contract.unpaid_amount) if contract.unpaid_amount else 0,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "sign_date": contract.sign_date.isoformat() if contract.sign_date else None,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "department": department,
            "source": source,
        }

    def _to_detail(self, contract) -> dict:
        base = self._to_response(contract)
        # Override paid_amount with dynamic calculation
        # (requires caller to call async after construction, handled in get_contract)
        all_docs = contract.documents or []
        base.update({
            "customer_id": str(contract.customer_id),
            "our_signatory": contract.our_signatory,
            "customer_signatory": contract.customer_signatory,
            "content": contract.content,
            "remark": contract.remark,
            "attachment_path": contract.attachment_path,
            "attachment_name": contract.attachment_name,
            "created_by": str(contract.created_by) if contract.created_by else None,
            "documents": [
                {
                    "id": str(d.id),
                    "doc_no": d.doc_no,
                    "doc_type": d.doc_type,
                    "project_name": d.project_name,
                    "total_amount": float(d.total_amount) if d.total_amount else 0,
                }
                for d in all_docs
            ],
            # Backward-compat: keep orders/quotes split for frontend
            "orders": [
                {
                    "id": str(d.id),
                    "order_no": d.doc_no,
                    "project_name": d.project_name,
                    "total_amount": float(d.total_amount) if d.total_amount else 0,
                }
                for d in all_docs if d.doc_type == "order"
            ],
            "quotes": [
                {
                    "id": str(d.id),
                    "quote_no": d.doc_no,
                    "project_name": d.project_name,
                    "total_amount": float(d.total_amount) if d.total_amount else 0,
                }
                for d in all_docs if d.doc_type == "quote"
            ],
        })
        return base

    async def list_contracts(
        self, page: int, page_size: int, status: str | None = None,
        keyword: str | None = None, customer_id: str | None = None,
        contract_type: str | None = None,
        exclude_contract_type: str | None = None,
    ) -> tuple[list, int]:
        skip = (page - 1) * page_size
        contracts, total = await self.repo.list_contracts(
            skip=skip, limit=page_size, status=status, keyword=keyword, customer_id=customer_id,
            contract_type=contract_type, exclude_contract_type=exclude_contract_type,
        )
        # Auto-complete contracts that are fully paid
        await self._auto_complete_if_paid(contracts)

        # Batch-calculate paid_amount and framework totals for all contracts in this page
        cids = [c.id for c in contracts]
        paid_map = await self._batch_paid_amounts(cids)
        fw_ids = [c.id for c in contracts if c.contract_type == "框架合同"]
        fw_total_map = await self._batch_framework_totals(fw_ids) if fw_ids else {}
        result = []
        for c in contracts:
            resp = self._to_response(c)
            paid = paid_map.get(c.id, 0.0)
            # 框架合同：金额 = 子项目合计
            if c.contract_type == "框架合同":
                resp["total_amount"] = fw_total_map.get(c.id, 0.0)
            resp["paid_amount"] = paid
            resp["unpaid_amount"] = max(0, resp["total_amount"] - paid)
            result.append(resp)
        return result, total

    async def get_contract(self, contract_id: UUID) -> dict | None:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            return None
        # Auto-complete if fully paid
        await self._auto_complete_if_paid([contract])
        result = self._to_detail(contract)
        # 框架合同：金额 = 子项目合计
        if contract.contract_type == "框架合同":
            result["total_amount"] = await self._calc_framework_total(contract_id)
        # Override paid_amount with actual payments on linked documents
        result["paid_amount"] = await self._calc_paid_amount(contract_id)
        result["unpaid_amount"] = max(0, result["total_amount"] - result["paid_amount"])
        return result

    def _combine_document_ids(self, data: dict) -> list[UUID]:
        """Combine order_ids + quote_ids (backward compat) or use document_ids."""
        # If document_ids provided directly, use it
        if "document_ids" in data:
            raw = data.pop("document_ids", [])
            return [UUID(did) for did in (raw or [])]
        # Fallback: combine order_ids + quote_ids
        order_ids = data.pop("order_ids", [])
        quote_ids = data.pop("quote_ids", [])
        return [UUID(oid) for oid in (order_ids or [])] + [UUID(qid) for qid in (quote_ids or [])]

    async def create_contract(self, data: dict) -> dict:
        data["contract_no"] = await generate_contract_no(self.db)
        data["document_ids"] = self._combine_document_ids(data)
        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        # Convert date strings to date objects
        for field in ("sign_date", "start_date", "end_date"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = date.fromisoformat(val)
                except ValueError:
                    data[field] = datetime.fromisoformat(val).date()

        contract = await self.repo.create(data)
        # Re-fetch to load secondary relationships (documents)
        contract = await self.repo.get_by_id(contract.id)
        # Auto-complete if fully paid
        await self._auto_complete_if_paid([contract])
        result = self._to_detail(contract)
        result["paid_amount"] = await self._calc_paid_amount(contract.id)
        result["unpaid_amount"] = max(0, result["total_amount"] - result["paid_amount"])
        return result

    async def update_contract(self, contract_id: UUID, data: dict) -> dict:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")

        # Handle document_ids update (also support backward-compat order_ids/quote_ids)
        has_doc_update = any(k in data for k in ("document_ids", "order_ids", "quote_ids"))
        if has_doc_update:
            data["document_ids"] = self._combine_document_ids(data)

        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        # Convert date strings to date objects
        for field in ("sign_date", "start_date", "end_date"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = date.fromisoformat(val)
                except ValueError:
                    data[field] = datetime.fromisoformat(val).date()

        contract = await self.repo.update(contract, data)
        # Re-fetch to load secondary relationships after updates
        contract = await self.repo.get_by_id(contract.id)
        # Auto-complete if fully paid
        await self._auto_complete_if_paid([contract])
        result = self._to_detail(contract)
        result["paid_amount"] = await self._calc_paid_amount(contract_id)
        result["unpaid_amount"] = max(0, result["total_amount"] - result["paid_amount"])
        return result

    async def update_attachment(self, contract_id: UUID, path: str | None, name: str | None) -> dict:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")
        contract.attachment_path = path
        contract.attachment_name = name
        await self.db.flush()
        return self._to_detail(contract)

    async def delete_contract(self, contract_id: UUID) -> bool:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            return False
        await self.repo.soft_delete(contract)
        return True

    async def change_status(self, contract_id: UUID, to_status: str, reason: str | None = None) -> dict:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")

        allowed = CONTRACT_TRANSITIONS.get(contract.status, [])
        if to_status not in allowed:
            raise ValueError(f"合同状态不允许从「{contract.status}」变更为「{to_status}」")

        contract.status = to_status
        await self.db.flush()
        # Re-fetch to load secondary relationships
        contract = await self.repo.get_by_id(contract.id)
        return self._to_detail(contract)
