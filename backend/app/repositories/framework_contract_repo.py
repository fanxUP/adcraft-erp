from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.framework_contract import (
    FrameworkContractProject,
    FrameworkContractProjectOrder,
    FrameworkContractProjectQuote,
)


class FrameworkContractProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: UUID) -> FrameworkContractProject | None:
        result = await self.db.execute(
            select(FrameworkContractProject)
            .where(FrameworkContractProject.id == project_id, FrameworkContractProject.deleted_at.is_(None))
            .options(
                selectinload(FrameworkContractProject.orders),
                selectinload(FrameworkContractProject.quotes),
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
            selectinload(FrameworkContractProject.orders),
            selectinload(FrameworkContractProject.quotes),
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(FrameworkContractProject.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create(self, data: dict) -> FrameworkContractProject:
        order_ids = data.pop("order_ids", [])
        quote_ids = data.pop("quote_ids", [])
        project = FrameworkContractProject(**data)
        if project.id is None:
            project.id = uuid4()
        self.db.add(project)

        for oid in order_ids:
            self.db.add(FrameworkContractProjectOrder(project_id=project.id, order_id=oid))
        for qid in quote_ids:
            self.db.add(FrameworkContractProjectQuote(project_id=project.id, quote_id=qid))

        await self.db.flush()
        return project

    async def update(self, project: FrameworkContractProject, data: dict) -> FrameworkContractProject:
        order_ids = data.pop("order_ids", None)
        quote_ids = data.pop("quote_ids", None)

        for key, value in data.items():
            setattr(project, key, value)

        if order_ids is not None:
            result = await self.db.execute(
                select(FrameworkContractProjectOrder).where(
                    FrameworkContractProjectOrder.project_id == project.id
                )
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for oid in order_ids:
                self.db.add(FrameworkContractProjectOrder(project_id=project.id, order_id=oid))

        if quote_ids is not None:
            result = await self.db.execute(
                select(FrameworkContractProjectQuote).where(
                    FrameworkContractProjectQuote.project_id == project.id
                )
            )
            for row in result.scalars().all():
                await self.db.delete(row)
            for qid in quote_ids:
                self.db.add(FrameworkContractProjectQuote(project_id=project.id, quote_id=qid))

        await self.db.flush()
        return project

    async def soft_delete(self, project: FrameworkContractProject) -> FrameworkContractProject:
        project.deleted_at = datetime.now()
        await self.db.flush()
        return project
