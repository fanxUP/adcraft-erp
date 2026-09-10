"""Persistence helpers for order-level task visibility assignments."""

import uuid
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.order_task_assignee import OrderTaskAssignee


class OrderTaskAssigneeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_order(self, document_id: UUID) -> list[OrderTaskAssignee]:
        result = await self.db.execute(
            select(OrderTaskAssignee)
            .where(OrderTaskAssignee.document_id == document_id)
            .order_by(OrderTaskAssignee.created_at, OrderTaskAssignee.employee_id)
        )
        return list(result.scalars().all())

    async def list_for_order_with_employees(self, document_id: UUID) -> list[tuple[OrderTaskAssignee, Employee]]:
        result = await self.db.execute(
            select(OrderTaskAssignee, Employee)
            .join(Employee, Employee.id == OrderTaskAssignee.employee_id)
            .where(OrderTaskAssignee.document_id == document_id)
            .order_by(Employee.name, Employee.employee_no)
        )
        return list(result.all())

    async def replace(
        self,
        document_id: UUID,
        employee_ids: list[UUID],
        assigned_by: UUID | None,
    ) -> None:
        await self.db.execute(
            delete(OrderTaskAssignee).where(
                OrderTaskAssignee.document_id == document_id
            )
        )
        if employee_ids:
            await self.db.execute(
                insert(OrderTaskAssignee),
                [
                    {
                        "id": uuid.uuid4(),
                        "document_id": document_id,
                        "employee_id": employee_id,
                        "assigned_by": assigned_by,
                    }
                    for employee_id in employee_ids
                ],
            )
        await self.db.flush()
