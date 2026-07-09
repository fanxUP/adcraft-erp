from uuid import UUID
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.outsource_repo import OutsourceVendorRepository, OutsourceTaskRepository, OutsourcePaymentRepository
from app.services.number_generator import generate_vendor_no, generate_outsource_task_no, generate_outsource_payment_no
from app.models.outsource import OutsourceVendor


class OutsourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_repo = OutsourceVendorRepository(db)
        self.task_repo = OutsourceTaskRepository(db)
        self.payment_repo = OutsourcePaymentRepository(db)

    # ── Vendor ──

    async def list_vendors(self, page: int, page_size: int, keyword: str | None = None,
                           service_type: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        vendors, total = await self.vendor_repo.list_vendors(skip, page_size, keyword, service_type)
        return [self._vendor_to_dict(v) for v in vendors], total

    async def get_vendor(self, vendor_id: UUID) -> dict | None:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            return None
        return self._vendor_to_dict(vendor)

    async def create_vendor(self, data: dict) -> dict:
        data["vendor_no"] = await generate_vendor_no(self.db)
        vendor = await self.vendor_repo.create(data)
        return self._vendor_to_dict(vendor)

    async def update_vendor(self, vendor_id: UUID, data: dict) -> dict:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("外协商不存在")
        vendor = await self.vendor_repo.update(vendor, data)
        return self._vendor_to_dict(vendor)

    async def delete_vendor(self, vendor_id: UUID) -> bool:
        vendor = await self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            return False
        await self.vendor_repo.soft_delete(vendor)
        return True

    # ── Task ──

    async def list_tasks(self, page: int, page_size: int, status: str | None = None,
                         vendor_id: UUID | None = None, order_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        tasks, total = await self.task_repo.list_tasks(skip, page_size, status, vendor_id, order_id)
        result = []
        for t in tasks:
            vname = await self._task_vendor_name(t)
            result.append(self._task_to_dict(t, vname))
        return result, total

    async def _task_vendor_name(self, task) -> str | None:
        """Load vendor name explicitly to avoid async lazy loading issues."""
        return await self._vendor_name(task.vendor_id)

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    async def create_task(self, data: dict) -> dict:
        data["task_no"] = await generate_outsource_task_no(self.db)
        if "quantity" not in data:
            data["quantity"] = 1
        qty = Decimal(str(data.get("quantity", 1)))
        price = Decimal(str(data.get("unit_price", 0)))
        data["total_amount"] = float(qty * price)
        task = await self.task_repo.create(data)
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    async def update_task(self, task_id: UUID, data: dict) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在")
        # 编辑已取消的任务时自动恢复为待处理（重新激活）
        if task.status == "cancelled":
            data["status"] = "pending"
            data["completed_at"] = None
        # Recalculate total if price or quantity changed
        if "unit_price" in data:
            price = Decimal(str(data["unit_price"]))
            qty = Decimal(str(data.get("quantity", task.quantity)))
            data["total_amount"] = float(qty * price)
        elif "quantity" in data:
            qty = Decimal(str(data["quantity"]))
            price = Decimal(str(task.unit_price))
            data["total_amount"] = float(qty * price)
        task = await self.task_repo.update(task, data)
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    # ── Payment ──

    async def list_payments(self, page: int, page_size: int, vendor_id: UUID | None = None,
                            task_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        payments, total = await self.payment_repo.list_payments(skip, page_size, vendor_id, task_id)
        result = []
        for p in payments:
            vname = await self._vendor_name(p.vendor_id)
            result.append(self._payment_to_dict(p, vname))
        return result, total

    async def create_payment(self, data: dict) -> dict:
        data["payment_no"] = await generate_outsource_payment_no(self.db)
        payment = await self.payment_repo.create(data)
        vname = await self._vendor_name(payment.vendor_id)
        return self._payment_to_dict(payment, vname)

    async def _vendor_name(self, vendor_id: UUID) -> str | None:
        result = await self.db.execute(select(OutsourceVendor.name).where(OutsourceVendor.id == vendor_id))
        return result.scalar_one_or_none()

    # ── Helpers ──

    def _vendor_to_dict(self, v) -> dict:
        return {
            "id": str(v.id), "vendor_no": v.vendor_no,
            "name": v.name, "contact_person": v.contact_person,
            "phone": v.phone, "address": v.address,
            "service_type": v.service_type, "coop_rating": v.coop_rating,
            "remark": v.remark, "is_active": v.is_active,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }

    def _task_to_dict(self, t, vendor_name: str | None = None) -> dict:
        return {
            "id": str(t.id), "task_no": t.task_no,
            "vendor_id": str(t.vendor_id),
            "vendor_name": vendor_name,
            "order_id": str(t.order_id) if t.order_id else None,
            "task_type": t.task_type,
            "description": t.description,
            "quantity": t.quantity,
            "unit_price": float(t.unit_price),
            "total_amount": float(t.total_amount),
            "status": t.status,
            "expected_at": t.expected_at.isoformat() if t.expected_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "remark": t.remark,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    def _payment_to_dict(self, p, vendor_name: str | None = None) -> dict:
        return {
            "id": str(p.id), "payment_no": p.payment_no,
            "vendor_id": str(p.vendor_id),
            "vendor_name": vendor_name,
            "task_id": str(p.task_id) if p.task_id else None,
            "amount": float(p.amount),
            "payment_method": p.payment_method,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "remark": p.remark,
            "created_by": str(p.created_by) if p.created_by else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    # ── Cancel Task (admin only) ──

    async def cancel_task(self, task_id: UUID) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status in ("completed", "settled", "cancelled"):
            raise ValueError(f"当前状态「{task.status}」不允许取消")
        task.status = "cancelled"
        await self.db.flush()
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    # ── Revert Task (admin only: completed → in_progress) ──

    async def revert_task(self, task_id: UUID) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status != "completed":
            raise ValueError(f"当前状态「{task.status}」不允许退回，仅已完成的任务可以退回")
        task.status = "in_progress"
        task.completed_at = None
        await self.db.flush()
        vname = await self._task_vendor_name(task)
        return self._task_to_dict(task, vname)

    # ── Delete Task (admin only) ──

    async def delete_task(self, task_id: UUID) -> bool:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("外协任务不存在")
        if task.status != "cancelled":
            raise ValueError("仅已取消的外协任务可以删除")
        await self.db.delete(task)
        await self.db.flush()
        return True
