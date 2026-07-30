import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.department_repo import DepartmentRepository

logger = logging.getLogger(__name__)


class DepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DepartmentRepository(db)

    async def list_departments(self, keyword=None, parent_id=None, include_inactive=False):
        depts = await self.repo.list(keyword, parent_id, include_inactive)
        return [self._d(d) for d in depts]

    async def get_department(self, did: UUID):
        d = await self.repo.get_by_id(did)
        return self._d(d) if d else None

    async def create_department(self, data):
        existing = await self.repo.get_by_code(data["code"])
        if existing:
            raise ValueError(f"部门编码 {data['code']} 已存在")
        if data.get("parent_id"):
            parent = await self.repo.get_by_id(UUID(data["parent_id"]) if isinstance(data["parent_id"], str) else data["parent_id"])
            if not parent:
                raise ValueError("上级部门不存在")
            data["parent_id"] = UUID(data["parent_id"]) if isinstance(data["parent_id"], str) else data["parent_id"]
        return self._d(await self.repo.create(data))

    async def update_department(self, did: UUID, data):
        d = await self.repo.get_by_id(did)
        if not d:
            raise ValueError("部门不存在")
        if "code" in data and data["code"] and data["code"] != d.code:
            existing = await self.repo.get_by_code(data["code"])
            if existing:
                raise ValueError(f"部门编码 {data['code']} 已存在")
        if data.get("parent_id"):
            pid = UUID(data["parent_id"]) if isinstance(data["parent_id"], str) else data["parent_id"]
            if pid == did:
                raise ValueError("上级部门不能是自己")
            data["parent_id"] = pid
        return self._d(await self.repo.update(d, data))

    async def delete_department(self, did: UUID):
        d = await self.repo.get_by_id(did)
        if not d:
            return False
        # Check children
        children = await self.repo.list(parent_id=did, include_inactive=True)
        if children:
            raise ValueError(f"部门 '{d.name}' 下有子部门，无法删除")
        await self.repo.soft_delete(d)
        return True

    def _d(self, d):
        return {
            "id": str(d.id),
            "name": d.name,
            "code": d.code,
            "parent_id": str(d.parent_id) if d.parent_id else None,
            "sort_order": d.sort_order,
            "description": d.description,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
