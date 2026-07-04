from datetime import datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project_cost import ProjectCost
from app.models.task import Attachment
from app.repositories.project_cost_repo import ProjectCostRepository
from app.repositories.task_repo import AttachmentRepository
from app.services.number_generator import generate_project_cost_no


class ProjectCostService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectCostRepository(db)
        self.attachment_repo = AttachmentRepository(db)

    async def _sync_order_cost(self, order_id: UUID) -> None:
        """Re-calculate order cost from all sources (outsource + material stock + project costs)."""
        from app.services.order_service import OrderService
        order_svc = OrderService(self.db)
        await order_svc.auto_calculate_cost(order_id)

    async def list_costs(
        self,
        page: int,
        page_size: int,
        order_id: UUID | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list, int]:
        skip = (page - 1) * page_size
        costs, total = await self.repo.list_costs(skip, page_size, order_id, category, date_from, date_to)
        result = [self._to_dict(c) for c in costs]
        # Populate attachment counts
        if result:
            cost_ids = [c.id for c in costs]
            counts = await self._get_attachment_counts(cost_ids)
            for d in result:
                d["attachment_count"] = counts.get(d["id"], 0)
        return result, total

    async def get_cost(self, cost_id: UUID) -> dict | None:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            return None
        d = self._to_dict(c)
        atts = await self.attachment_repo.get_by_task("project_cost", cost_id)
        d["attachments"] = [
            {
                "id": str(a.id),
                "filename": a.filename,
                "file_path": a.file_path,
                "file_size": a.file_size,
                "file_type": a.file_type,
                "category": a.category,
                "uploaded_by": str(a.uploaded_by) if a.uploaded_by else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in atts
        ]
        d["attachment_count"] = len(atts)
        return d

    async def create_cost(self, data: dict, created_by: UUID) -> dict:
        order_id = UUID(data["order_id"])
        # Look up order to get customer_id and project_name
        result = await self.db.execute(
            select(Order.id, Order.customer_id, Order.project_name).where(Order.id == order_id)
        )
        order_row = result.one_or_none()
        if not order_row:
            raise ValueError("订单不存在")

        order_id_val, customer_id_val, project_name_val = order_row

        cost = ProjectCost(
            cost_no=await generate_project_cost_no(self.db),
            order_id=order_id_val,
            customer_id=customer_id_val,
            category=data["category"],
            amount=data["amount"],
            description=data.get("description"),
            cost_date=datetime.fromisoformat(data["cost_date"]) if data.get("cost_date") else None,
            receipt_url=data.get("receipt_url"),
            remark=data.get("remark"),
            created_by=created_by,
        )
        await self.repo.create(cost)
        await self._sync_order_cost(order_id)
        return {
            "id": str(cost.id),
            "cost_no": cost.cost_no,
            "order_id": str(cost.order_id),
            "customer_id": str(cost.customer_id) if cost.customer_id else None,
            "customer_name": None,  # populated by list query via relationship
            "project_name": project_name_val,
            "category": cost.category,
            "amount": float(cost.amount),
            "description": cost.description,
            "cost_date": cost.cost_date.isoformat() if cost.cost_date else None,
            "receipt_url": cost.receipt_url,
            "remark": cost.remark,
            "created_by": str(cost.created_by) if cost.created_by else None,
            "created_at": cost.created_at.isoformat() if cost.created_at else None,
        }

    async def update_cost(self, cost_id: UUID, data: dict) -> dict:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            raise ValueError("项目成本记录不存在")
        if "cost_date" in data and data["cost_date"] is not None:
            data = {**data, "cost_date": datetime.fromisoformat(data["cost_date"])}
        await self.repo.update(c, data)
        await self._sync_order_cost(c.order_id)
        # Re-fetch with relationships loaded for response
        c = await self.repo.get_by_id(cost_id)
        return self._to_dict(c)

    async def delete_cost(self, cost_id: UUID) -> None:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            raise ValueError("项目成本记录不存在")
        order_id = c.order_id
        await self.repo.soft_delete(c)
        await self._sync_order_cost(order_id)

    async def get_costs_summary(self, order_ids: list[UUID]) -> dict[str, float]:
        """Return {order_id: total_cost} for a batch of orders."""
        return await self.repo.get_costs_summary(order_ids)

    async def import_from_excel(self, file: BytesIO, created_by: UUID, order_id: UUID | None = None) -> dict:
        """Parse Excel file and create ProjectCost records.
        When order_id is provided, all rows are assigned to that order and the
        Excel only needs columns: 成本类别, 金额, 描述(可选), 成本日期(可选), 备注(可选).
        When order_id is None, the Excel must include column: 订单编号, 成本类别, 金额, ...
        """
        import openpyxl

        wb = openpyxl.load_workbook(file, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))  # Skip header

        created = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            if not row:
                continue
            try:
                if order_id:
                    # Import within order context — order_id pre-set
                    category = str(row[0]).strip() if row[0] else ""
                    amount = float(row[1]) if row[1] else 0
                    description = str(row[2]).strip() if len(row) > 2 and row[2] else None
                    cost_date_str = str(row[3]).strip() if len(row) > 3 and row[3] else None
                    remark = str(row[4]).strip() if len(row) > 4 and row[4] else None

                    if not category or amount <= 0:
                        errors.append({"row": i, "error": "成本类别和金额(>0)为必填项"})
                        continue

                    cost_date = None
                    if cost_date_str:
                        try:
                            cost_date = datetime.fromisoformat(cost_date_str)
                        except ValueError:
                            cost_date = datetime.strptime(cost_date_str, "%Y-%m-%d")

                    await self.create_cost({
                        "order_id": str(order_id),
                        "category": category,
                        "amount": amount,
                        "description": description,
                        "cost_date": cost_date.isoformat() if cost_date else None,
                        "remark": remark,
                    }, created_by)
                else:
                    # Standalone import — Excel must include order_no
                    if not row[0]:
                        continue
                    order_no = str(row[0]).strip()
                    category = str(row[1]).strip() if row[1] else ""
                    amount = float(row[2]) if row[2] else 0
                    description = str(row[3]).strip() if len(row) > 3 and row[3] else None
                    cost_date_str = str(row[4]).strip() if len(row) > 4 and row[4] else None
                    remark = str(row[5]).strip() if len(row) > 5 and row[5] else None

                    if not order_no or not category or amount <= 0:
                        errors.append({"row": i, "error": "订单编号、成本类别和金额(>0)为必填项"})
                        continue

                    # Look up order by order_no
                    order_result = await self.db.execute(select(Order).where(Order.order_no == order_no))
                    order = order_result.scalar_one_or_none()
                    if not order:
                        errors.append({"row": i, "error": f"订单编号「{order_no}」不存在"})
                        continue

                    cost_date = None
                    if cost_date_str:
                        try:
                            cost_date = datetime.fromisoformat(cost_date_str)
                        except ValueError:
                            cost_date = datetime.strptime(cost_date_str, "%Y-%m-%d")

                    await self.create_cost({
                        "order_id": str(order.id),
                        "category": category,
                        "amount": amount,
                        "description": description,
                        "cost_date": cost_date.isoformat() if cost_date else None,
                        "remark": remark,
                    }, created_by)
                created += 1
            except Exception as e:
                errors.append({"row": i, "error": str(e)})

        return {"created": created, "errors": errors}

    async def _get_attachment_counts(self, cost_ids: list[UUID]) -> dict[str, int]:
        """Return {cost_id_str: count} for a batch of costs."""
        if not cost_ids:
            return {}
        from sqlalchemy import func
        result = await self.db.execute(
            select(Attachment.related_id, func.count())
            .where(
                Attachment.related_type == "project_cost",
                Attachment.related_id.in_(cost_ids),
            )
            .group_by(Attachment.related_id)
        )
        return {str(row[0]): row[1] for row in result.all()}

    def _to_dict(self, c: ProjectCost) -> dict:
        return {
            "id": str(c.id),
            "cost_no": c.cost_no,
            "order_id": str(c.order_id),
            "customer_id": str(c.customer_id) if c.customer_id else None,
            "customer_name": c.customer.name if c.customer else None,
            "project_name": c.order.project_name if c.order else None,
            "category": c.category,
            "amount": float(c.amount),
            "description": c.description,
            "cost_date": c.cost_date.isoformat() if c.cost_date else None,
            "receipt_url": c.receipt_url,
            "remark": c.remark,
            "created_by": str(c.created_by) if c.created_by else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "attachment_count": 0,
        }
