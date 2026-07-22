from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.framework_contract import (
    FrameworkContractProject,
    FrameworkContractProjectDocument,
)


class FrameworkContractProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: UUID) -> FrameworkContractProject | None:
        result = await self.db.execute(
            select(FrameworkContractProject)
            .where(FrameworkContractProject.id == project_id, FrameworkContractProject.deleted_at.is_(None))
            .options(
                selectinload(FrameworkContractProject.documents),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_contract(
        self, contract_id: UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[FrameworkContractProject], int]:
        q = select(FrameworkContractProject).where(
            FrameworkContractProject.contract_id == contract_id,
            FrameworkContractProject.deleted_at.is_(None),
        ).options(
            selectinload(FrameworkContractProject.documents),
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(FrameworkContractProject.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> FrameworkContractProject:
        document_ids = data.pop("document_ids", [])
        project = FrameworkContractProject(**data)
        if project.id is None:
            project.id = uuid4()
        self.db.add(project)

        for did in document_ids:
            self.db.add(FrameworkContractProjectDocument(project_id=project.id, document_id=did))

        await self.db.flush()
        return project

    async def update(self, project: FrameworkContractProject, data: dict) -> FrameworkContractProject:
        document_ids = data.pop("document_ids", None)

        for key, value in data.items():
            setattr(project, key, value)

        if document_ids is not None:
            result = await self.db.execute(
                select(FrameworkContractProjectDocument).where(
                    FrameworkContractProjectDocument.project_id == project.id
                )
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for did in document_ids:
                self.db.add(FrameworkContractProjectDocument(project_id=project.id, document_id=did))

        await self.db.flush()
        return project

    async def soft_delete(self, project: FrameworkContractProject) -> FrameworkContractProject:
        project.deleted_at = datetime.now()
        await self.db.flush()
        return project
