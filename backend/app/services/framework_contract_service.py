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
        base.update({
            "orders": [
                {
                    "id": str(o.id),
                    "order_no": o.order_no,
                    "project_name": o.project_name,
                    "total_amount": float(o.total_amount) if o.total_amount else 0,
                }
                for o in (project.orders or [])
            ],
            "quotes": [
                {
                    "id": str(q.id),
                    "quote_no": q.quote_no,
                    "project_name": q.project_name,
                    "total_amount": float(q.total_amount) if q.total_amount else 0,
                }
                for q in (project.quotes or [])
            ],
        })
        return base

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
        order_ids = data.get("order_ids", [])
        quote_ids = data.get("quote_ids", [])
        data["order_ids"] = [UUID(oid) for oid in (order_ids or [])]
        data["quote_ids"] = [UUID(qid) for qid in (quote_ids or [])]

        project = await self.repo.create(data)
        project = await self.repo.get_by_id(project.id)
        await self._sync_contract_total(project.contract_id)
        return self._to_detail(project)

    async def update_project(self, project_id: UUID, data: dict) -> dict:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ValueError("框架合同项目不存在")

        if data.get("order_ids") is not None:
            data["order_ids"] = [UUID(oid) for oid in data["order_ids"]]
        if data.get("quote_ids") is not None:
            data["quote_ids"] = [UUID(qid) for qid in data["quote_ids"]]

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
            contract.unpaid_amount = max(0, total - (float(contract.paid_amount) if contract.paid_amount else 0))
            await self.db.flush()

    async def update_attachment(self, project_id: UUID, path: str | None, name: str | None) -> dict:
        project = await self.repo.get_by_id(project_id)
        if not project:
            raise ValueError("框架合同项目不存在")
        project.attachment_path = path
        project.attachment_name = name
        await self.db.flush()
        return self._to_detail(project)
