from datetime import date, datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contract_repo import ContractRepository
from app.schemas.contract import ContractListResponse, ContractDetailResponse
from app.services.number_generator import generate_contract_no
from app.services.business_document_service import BusinessDocumentService
from app.domain.workflows import CONTRACT_WORKFLOW, allowed_targets


# 状态流转映射
CONTRACT_TRANSITIONS = CONTRACT_WORKFLOW


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
        d = ContractListResponse.model_validate(contract).model_dump(mode="json")
        docs = contract.documents or []
        departments = list({d.department for d in docs if d.department})
        d["department"] = "、".join(departments) if departments else ""
        d["source"] = "订单" if docs else ""
        return d

    def _to_detail(self, contract) -> dict:
        d = ContractDetailResponse.model_validate(contract).model_dump(mode="json")
        docs = contract.documents or []
        departments = list({d.department for d in docs if d.department})
        d["department"] = "、".join(departments) if departments else ""
        d["source"] = "订单" if docs else ""
        d["documents"] = [BusinessDocumentService._to_ref(d) for d in docs]
        d["orders"] = [BusinessDocumentService._to_ref(d) for d in docs if d.doc_type == "order"]
        return d

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
        # 所有合同：金额 = 子项目合计（无子项目则用合同自身金额）
        all_ids = [c.id for c in contracts]
        fw_total_map = await self._batch_framework_totals(all_ids) if all_ids else {}
        result = []
        for c in contracts:
            resp = self._to_response(c)
            paid = paid_map.get(c.id, 0.0)
            proj_total = fw_total_map.get(c.id)
            if proj_total is not None and proj_total > 0:
                resp["total_amount"] = proj_total
            resp["paid_amount"] = paid
            resp["unpaid_amount"] = max(0, resp["total_amount"] - paid)
            result.append(resp)
        return result, total

    async def list_orders_without_contract(
        self, page: int, page_size: int, keyword: str | None = None
    ) -> tuple[list, int]:
        """未被任何合同/框架合同项目关联的订单（用于「未建立合同订单」列表）。"""
        skip = (page - 1) * page_size
        docs, total = await self.repo.list_orders_without_contract(
            skip=skip, limit=page_size, keyword=keyword
        )
        result = []
        for d in docs:
            item = BusinessDocumentService._to_ref(d)
            item["customer_id"] = str(d.customer_id) if d.customer_id else None
            item["created_at"] = d.created_at.isoformat() if d.created_at else None
            result.append(item)
        return result, total

    async def _load_linkable_orders(self, uids: list[UUID], contract_id: UUID) -> list[UUID]:
        """校验并返回可关联的订单 id（跳过目标合同已关联的，拒绝已关联其他合同/框架项目的）。

        只统计未删除合同/框架项目的关联：软删除合同不再占用订单。
        """
        from sqlalchemy import select
        from app.models.business_document import BusinessDocument
        from app.models.contract import Contract, ContractDocument
        from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument

        result = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id.in_(uids),
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.doc_type == "order",
                BusinessDocument.status != "cancelled",
            )
        )
        docs = result.scalars().all()
        found = {d.id for d in docs}
        missing = [u for u in uids if u not in found]
        if missing:
            raise ValueError(f"订单不存在、已删除或已取消: {[str(m) for m in missing]}")

        # 已关联到其他（未删除）合同
        other = await self.db.execute(
            select(ContractDocument.document_id)
            .join(Contract, Contract.id == ContractDocument.contract_id)
            .where(
                ContractDocument.document_id.in_(uids),
                ContractDocument.contract_id != contract_id,
                Contract.deleted_at.is_(None),
            )
        )
        other_linked = {row for row in other.scalars().all()}
        if other_linked:
            raise ValueError(f"订单已关联其他合同: {[str(o) for o in other_linked]}")

        # 已关联到其他框架合同的子项目（未删除）
        fw_other = await self.db.execute(
            select(FrameworkContractProjectDocument.document_id)
            .join(FrameworkContractProject, FrameworkContractProject.id == FrameworkContractProjectDocument.project_id)
            .where(
                FrameworkContractProjectDocument.document_id.in_(uids),
                FrameworkContractProject.contract_id != contract_id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )
        fw_other_linked = {row for row in fw_other.scalars().all()}
        if fw_other_linked:
            raise ValueError(f"订单已关联其他框架合同: {[str(o) for o in fw_other_linked]}")

        # 跳过目标合同已关联的（幂等）：contract_documents + 目标框架合同的子项目
        target = await self.db.execute(
            select(ContractDocument.document_id).where(
                ContractDocument.contract_id == contract_id,
                ContractDocument.document_id.in_(uids),
            )
        )
        target_linked = {row for row in target.scalars().all()}

        fw_target = await self.db.execute(
            select(FrameworkContractProjectDocument.document_id)
            .join(FrameworkContractProject, FrameworkContractProject.id == FrameworkContractProjectDocument.project_id)
            .where(
                FrameworkContractProjectDocument.document_id.in_(uids),
                FrameworkContractProject.contract_id == contract_id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )
        target_linked |= {row for row in fw_target.scalars().all()}
        return [u for u in uids if u not in target_linked]

    async def link_orders_to_contract(self, contract_id: UUID, order_ids: list[str]) -> dict:
        """把订单加入框架合同：自动为每个订单创建子项目并关联（普通合同不支持）。"""
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")
        if contract.contract_type != "框架合同":
            raise ValueError("普通合同请通过「新建合同」关联订单")

        uids = [UUID(oid) for oid in order_ids]
        linkable = await self._load_linkable_orders(uids, contract_id)
        if linkable:
            for oid in linkable:
                await self._add_order_as_project(contract, oid)
        contract = await self.repo.get_by_id(contract.id)
        # Auto-complete if fully paid
        await self._auto_complete_if_paid([contract])
        result = self._to_detail(contract)
        result["total_amount"] = await self._calc_framework_total(contract.id)
        result["paid_amount"] = await self._calc_paid_amount(contract.id)
        result["unpaid_amount"] = max(0, result["total_amount"] - result["paid_amount"])
        return result

    async def _add_order_as_project(self, contract, order_id: UUID) -> None:
        """把订单作为子项目加入框架合同（复用框架项目服务：建子项目 + 关联订单 + 同步合同金额）。"""
        from sqlalchemy import select
        from app.models.business_document import BusinessDocument
        from app.services.framework_contract_service import FrameworkContractService

        result = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return
        fw_service = FrameworkContractService(self.db)
        await fw_service.create_project({
            "contract_id": str(contract.id),
            "customer_id": str(contract.customer_id or order.customer_id),
            "customer_name": contract.customer_name or order.customer_name,
            "department": order.department,
            "project_name": order.project_name,
            "project_amount": float(order.total_amount or 0),
            "order_ids": [str(order.id)],
        })

    async def get_contract(self, contract_id: UUID) -> dict | None:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            return None
        # Auto-complete if fully paid
        await self._auto_complete_if_paid([contract])
        result = self._to_detail(contract)
        # 所有合同：金额 = 子项目合计（无子项目则用合同自身金额）
        proj_total = await self._calc_framework_total(contract_id)
        if proj_total > 0:
            result["total_amount"] = proj_total
        # Override paid_amount with actual payments on linked documents
        result["paid_amount"] = await self._calc_paid_amount(contract_id)
        result["unpaid_amount"] = max(0, result["total_amount"] - result["paid_amount"])
        return result

    def _combine_document_ids(self, data: dict) -> list[UUID]:
        """Extract order_ids from the payload. Supports both order_ids and document_ids keys."""
        if "document_ids" in data:
            raw = data.pop("document_ids", [])
            return [UUID(did) for did in (raw or [])]
        order_ids = data.pop("order_ids", [])
        return [UUID(oid) for oid in (order_ids or [])]

    async def create_contract(self, data: dict) -> dict:
        data["contract_no"] = await generate_contract_no(self.db)
        if "order_ids" in data or "document_ids" in data:
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
        has_doc_update = any(k in data for k in ("document_ids", "order_ids"))
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

        allowed = allowed_targets(CONTRACT_TRANSITIONS, contract.status)
        if to_status not in allowed:
            raise ValueError(f"合同状态不允许从「{contract.status}」变更为「{to_status}」")

        contract.status = to_status
        await self.db.flush()
        # Re-fetch to load secondary relationships
        contract = await self.repo.get_by_id(contract.id)
        return self._to_detail(contract)
