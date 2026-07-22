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
        base.update({
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
        return result, total

    async def get_project(self, project_id: UUID) -> dict | None:
        project = await self.repo.get_by_id(project_id)
        if not project:
            return None
        return self._to_detail(project)

    async def create_project(self, data: dict) -> dict:
        data["contract_id"] = UUID(data["contract_id"])
        data["customer_id"] = UUID(data["customer_id"])
        data["document_ids"] = self._combine_document_ids(data)

        project = await self.repo.create(data)
        project = await self.repo.get_by_id(project.id)
        await self._sync_contract_total(project.contract_id)
        return self._to_detail(project)

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
        return self._to_detail(project)

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
