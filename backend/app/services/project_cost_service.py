from datetime import datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

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

        debt_amount = data.get("debt_amount")
        if debt_amount is not None:
            debt_amount = float(debt_amount)
        else:
            debt_amount = 0

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
            order_item_id=UUID(data["order_item_id"]) if data.get("order_item_id") else None,
            payment_method=data.get("payment_method"),
            payee_company_name=data.get("payee_company_name"),
            debt_amount=debt_amount,
            is_debt=debt_amount > 0,
            is_settled=False,
            created_by=created_by,
        )
        await self.repo.create(cost)
        await self._sync_order_cost(order_id)
        return {
            "id": str(cost.id),
            "cost_no": cost.cost_no,
            "order_id": str(cost.order_id),
            "order_item_id": str(cost.order_item_id) if cost.order_item_id else None,
            "order_item_name": cost.order_item.item_name if cost.order_item else None,
            "customer_id": str(cost.customer_id) if cost.customer_id else None,
            "customer_name": None,  # populated by list query via relationship
            "project_name": project_name_val,
            "category": cost.category,
            "amount": float(cost.amount),
            "payment_method": cost.payment_method,
            "payee_company_name": cost.payee_company_name,
            "debt_amount": float(cost.debt_amount) if cost.debt_amount else None,
            "is_debt": cost.is_debt,
            "is_settled": cost.is_settled,
            "settled_at": cost.settled_at.isoformat() if cost.settled_at else None,
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

    async def list_debts(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        is_settled: bool | None = None,
    ) -> tuple[list, int]:
        """List all cost debts."""
        from sqlalchemy import or_
        from app.models.order import Order as OrderModel
        from app.models.customer import Customer as CustomerModel

        skip = (page - 1) * page_size
        q = select(ProjectCost).options(
            selectinload(ProjectCost.order),
            selectinload(ProjectCost.customer),
        ).where(
            ProjectCost.deleted_at.is_(None),
            ProjectCost.is_debt == True,
        )
        if is_settled is not None:
            q = q.where(ProjectCost.is_settled == is_settled)
        if keyword:
            fuzzy = f"%{keyword}%"
            q = q.join(ProjectCost.order).join(ProjectCost.customer, isouter=True).where(
                or_(
                    OrderModel.order_no.ilike(fuzzy),
                    OrderModel.project_name.ilike(fuzzy),
                    CustomerModel.name.ilike(fuzzy),
                )
            )

        # Count
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(ProjectCost.created_at.desc()).offset(skip).limit(page_size)
        result = await self.db.execute(q)
        costs = list(result.scalars().all())

        result_list = []
        for c in costs:
            d = self._to_dict(c)
            d["order_no"] = c.order.order_no if c.order else None
            d["customer_name"] = c.customer.name if c.customer else None
            result_list.append(d)
        return result_list, total

    async def settle_debt(self, cost_id: UUID, settle_data: dict) -> dict:
        """Settle a cost debt (write-off)."""
        from datetime import datetime, timezone

        c = await self.repo.get_by_id(cost_id)
        if not c:
            raise ValueError("成本记录不存在")
        if not c.is_debt:
            raise ValueError("该记录不是欠款记录")
        if c.is_settled:
            raise ValueError("该欠款已结清")

        c.is_settled = True
        c.settled_at = datetime.now(timezone.utc)
        c.payment_method = settle_data.get("payment_method", c.payment_method or "转账支付")
        if settle_data.get("remark"):
            c.remark = (c.remark or "") + f" [结清: {settle_data['remark']}]"
        await self.db.flush()

        # Also create a formal cost entry for the settled debt amount
        from app.services.number_generator import generate_project_cost_no
        settle_cost = ProjectCost(
            cost_no=await generate_project_cost_no(self.db),
            order_id=c.order_id,
            customer_id=c.customer_id,
            category=c.category,
            amount=settle_data.get("settle_amount", float(c.debt_amount or 0)),
            payment_method=settle_data.get("payment_method", "转账支付"),
            debt_amount=0,
            is_debt=False,
            is_settled=False,
            description=f"欠款冲红 - 原成本编号 {c.cost_no}",
            cost_date=datetime.now(timezone.utc),
            remark=settle_data.get("remark"),
            created_by=c.created_by,
        )
        await self.repo.create(settle_cost)
        await self._sync_order_cost(c.order_id)

        return self._to_dict(c)

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
            "order_item_id": str(c.order_item_id) if c.order_item_id else None,
            "order_item_name": c.order_item.item_name if c.order_item else None,
            "customer_id": str(c.customer_id) if c.customer_id else None,
            "customer_name": c.customer.name if c.customer else None,
            "project_name": c.order.project_name if c.order else None,
            "category": c.category,
            "amount": float(c.amount),
            "payment_method": c.payment_method,
            "payee_company_name": c.payee_company_name,
            "debt_amount": float(c.debt_amount) if c.debt_amount else None,
            "is_debt": c.is_debt,
            "is_settled": c.is_settled,
            "settled_at": c.settled_at.isoformat() if c.settled_at else None,
            "description": c.description,
            "cost_date": c.cost_date.isoformat() if c.cost_date else None,
            "receipt_url": c.receipt_url,
            "remark": c.remark,
            "created_by": str(c.created_by) if c.created_by else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "attachment_count": 0,
        }
