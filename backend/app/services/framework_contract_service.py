from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.framework_contract_repo import FrameworkContractProjectRepository


class FrameworkContractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FrameworkContractProjectRepository(db)

    def _to_response(self, project) -> dict:
        return {
            "id": str(project.id),
            "contract_id": str(project.contract_id),
            "customer_id": str(project.customer_id),
            "customer_name": project.customer_name,
            "department": project.department,
            "project_name": project.project_name,
            "project_amount": float(project.project_amount) if project.project_amount else 0,
            "remark": project.remark,
            "attachment_path": project.attachment_path,
            "attachment_name": project.attachment_name,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }

    def _to_detail(self, project) -> dict:
        base = self._to_response(project)
        all_docs = project.documents or []
        doc_types = {d.doc_type for d in all_docs}
        if "order" in doc_types and "quote" in doc_types:
            source = "订单+报价"
        elif "order" in doc_types:
            source = "订单"
        elif "quote" in doc_types:
            source = "报价"
        else:
            source = ""
        base.update({
            "source": source,
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

    def _combine_document_ids(self, data: dict) -> list[UUID]:
        """Combine order_ids + quote_ids (backward compat) or use document_ids."""
        if "document_ids" in data:
            raw = data.pop("document_ids", [])
            return [UUID(did) for did in (raw or [])]
        order_ids = data.pop("order_ids", [])
        quote_ids = data.pop("quote_ids", [])
        return [UUID(oid) for oid in (order_ids or [])] + [UUID(qid) for qid in (quote_ids or [])]

    async def list_projects(self, contract_id: UUID, page: int, page_size: int) -> tuple[list, int]:
        skip = (page - 1) * page_size
        projects, total = await self.repo.list_by_contract(contract_id, skip=skip, limit=page_size)
        result = [self._to_detail(p) for p in projects]

        # 批量计算已收/未收金额
        pids = [p.id for p in projects]
        paid_map = await self._batch_project_paid_amounts(pids) if pids else {}
        for item in result:
            paid = paid_map.get(item["id"], 0.0)
            item["paid_amount"] = paid
            item["unpaid_amount"] = max(0, item["project_amount"] - paid)

        return result, total

    async def _batch_project_paid_amounts(self, project_ids: list[UUID]) -> dict[UUID, float]:
        """批量计算框架合同项目的已收金额（来自关联单据的收款）"""
        if not project_ids:
            return {}
        from sqlalchemy import select, func
        from app.models.payment import Payment
        from app.models.framework_contract import FrameworkContractProjectDocument

        result = await self.db.execute(
            select(
                FrameworkContractProjectDocument.project_id,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .select_from(Payment)
            .join(FrameworkContractProjectDocument,
                  FrameworkContractProjectDocument.document_id == Payment.document_id)
            .where(
                FrameworkContractProjectDocument.project_id.in_(project_ids),
                Payment.is_voided == False,
            )
            .group_by(FrameworkContractProjectDocument.project_id)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    async def list_contract_orders(self, contract_id: UUID) -> list[dict]:
        """获取框架合同下所有项目关联的订单列表"""
        from sqlalchemy import select
        from app.models.business_document import BusinessDocument
        from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument

        result = await self.db.execute(
            select(BusinessDocument)
            .distinct()
            .join(FrameworkContractProjectDocument,
                  FrameworkContractProjectDocument.document_id == BusinessDocument.id)
            .join(FrameworkContractProject,
                  FrameworkContractProjectDocument.project_id == FrameworkContractProject.id)
            .where(
                FrameworkContractProject.contract_id == contract_id,
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
            )
            .order_by(BusinessDocument.created_at.desc())
        )
        orders = result.scalars().all()
        return [
            {
                "id": str(o.id),
                "order_no": o.doc_no,
                "project_name": o.project_name,
                "total_amount": float(o.total_amount),
                "paid_amount": float(o.paid_amount),
                "unpaid_amount": float(o.unpaid_amount),
                "status": o.status,
            }
            for o in orders
        ]

    async def get_project(self, project_id: UUID) -> dict | None:
        project = await self.repo.get_by_id(project_id)
        if not project:
            return None
        result = self._to_detail(project)
        paid_map = await self._batch_project_paid_amounts([project_id])
        paid = paid_map.get(result["id"], 0.0)
        result["paid_amount"] = paid
        result["unpaid_amount"] = max(0, result["project_amount"] - paid)
        return result

    async def create_project(self, data: dict) -> dict:
        data["contract_id"] = UUID(data["contract_id"])
        data["customer_id"] = UUID(data["customer_id"])
        data["document_ids"] = self._combine_document_ids(data)

        project = await self.repo.create(data)
        project = await self.repo.get_by_id(project.id)
        await self._sync_contract_total(project.contract_id)
        result = self._to_detail(project)
        result["paid_amount"] = 0.0
        result["unpaid_amount"] = result["project_amount"]
        return result

    async def update_project(self, project_id: UUID, data: dict) -> dict:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ValueError("框架合同项目不存在")

        has_doc_update = any(k in data for k in ("document_ids", "order_ids", "quote_ids"))
        if has_doc_update:
            data["document_ids"] = self._combine_document_ids(data)

        project = await self.repo.update(project, data)
        project = await self.repo.get_by_id(project.id)
        await self._sync_contract_total(project.contract_id)
        result = self._to_detail(project)
        paid_map = await self._batch_project_paid_amounts([project_id])
        paid = paid_map.get(result["id"], 0.0)
        result["paid_amount"] = paid
        result["unpaid_amount"] = max(0, result["project_amount"] - paid)
        return result

    async def delete_project(self, project_id: UUID) -> bool:
        project = await self.repo.get_by_id(project_id)
        if not project:
            return False
        cid = project.contract_id
        await self.repo.soft_delete(project)
        await self._sync_contract_total(cid)
        return True

    async def _sync_contract_total(self, contract_id: UUID) -> None:
        """同步合同总金额 = 所有项目金额之和"""
        from sqlalchemy import select, func
        from app.models.framework_contract import FrameworkContractProject
        from app.models.contract import Contract

        result = await self.db.execute(
            select(func.coalesce(func.sum(FrameworkContractProject.project_amount), 0))
            .where(
                FrameworkContractProject.contract_id == contract_id,
                FrameworkContractProject.deleted_at.is_(None),
            )
        )
        total = float(result.scalar())

        contract = await self.db.get(Contract, contract_id)
        if contract:
            contract.total_amount = total
            # 不更新 paid_amount/unpaid_amount，API 响应中会动态计算
            await self.db.flush()

    async def update_attachment(self, project_id: UUID, path: str | None, name: str | None) -> dict:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ValueError("框架合同项目不存在")
        project.attachment_path = path
        project.attachment_name = name
        await self.db.flush()
        return self._to_detail(project)
