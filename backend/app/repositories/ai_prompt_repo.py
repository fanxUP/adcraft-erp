"""Repository for Prompt Center CRUD operations."""
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ai_prompt_template import AIPromptTemplate
from app.models.ai_prompt_version import AIPromptVersion
from app.models.ai_prompt_execution_log import AIPromptExecutionLog


class AIPromptTemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, template_id: UUID) -> Optional[AIPromptTemplate]:
        result = await self.db.execute(
            select(AIPromptTemplate).where(AIPromptTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_id: UUID, template_code: str) -> Optional[AIPromptTemplate]:
        result = await self.db.execute(
            select(AIPromptTemplate).where(
                AIPromptTemplate.tenant_id == tenant_id,
                AIPromptTemplate.template_code == template_code,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[AIPromptTemplate], int]:
        query = select(AIPromptTemplate).where(AIPromptTemplate.tenant_id == tenant_id)

        if category:
            query = query.where(AIPromptTemplate.category == category)
        if search:
            query = query.where(
                AIPromptTemplate.template_code.ilike(f"%{search}%")
                | AIPromptTemplate.template_name.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AIPromptTemplate.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(self, tenant_id: UUID, data: dict, created_by: Optional[UUID] = None) -> AIPromptTemplate:
        template = AIPromptTemplate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_by=created_by or tenant_id,
            **data,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update(self, template_id: UUID, data: dict) -> Optional[AIPromptTemplate]:
        data["version"] = AIPromptTemplate.version + 1
        result = await self.db.execute(
            update(AIPromptTemplate)
            .where(AIPromptTemplate.id == template_id)
            .values(**data)
            .returning(AIPromptTemplate)
        )
        await self.db.flush()
        return result.scalar_one_or_none()

    async def delete(self, template_id: UUID) -> bool:
        result = await self.db.execute(
            delete(AIPromptTemplate).where(AIPromptTemplate.id == template_id)
        )
        return result.rowcount > 0


class AIPromptVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, version_id: UUID) -> Optional[AIPromptVersion]:
        result = await self.db.execute(
            select(AIPromptVersion).where(AIPromptVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_by_template(
        self, template_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[AIPromptVersion], int]:
        query = select(AIPromptVersion).where(AIPromptVersion.template_id == template_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AIPromptVersion.version_number.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_next_version_number(self, template_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(AIPromptVersion.version_number), 0) + 1).where(
                AIPromptVersion.template_id == template_id
            )
        )
        return result.scalar() or 1

    async def create(
        self, template_id: UUID, data: dict, created_by: Optional[UUID] = None
    ) -> AIPromptVersion:
        ver = AIPromptVersion(id=uuid.uuid4(), template_id=template_id, created_by=created_by, **data)
        self.db.add(ver)
        await self.db.flush()
        return ver

    async def update(self, version_id: UUID, data: dict) -> Optional[AIPromptVersion]:
        result = await self.db.execute(
            update(AIPromptVersion)
            .where(AIPromptVersion.id == version_id)
            .values(**data)
            .returning(AIPromptVersion)
        )
        await self.db.flush()
        return result.scalar_one_or_none()


class AIPromptExecutionLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> AIPromptExecutionLog:
        log = AIPromptExecutionLog(id=uuid.uuid4(), **data)
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        template_id: Optional[UUID] = None,
    ) -> tuple[list[AIPromptExecutionLog], int]:
        query = select(AIPromptExecutionLog).where(AIPromptExecutionLog.tenant_id == tenant_id)

        if template_id:
            query = query.where(AIPromptExecutionLog.template_id == template_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(AIPromptExecutionLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
