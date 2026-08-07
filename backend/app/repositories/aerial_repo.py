"""高空作业车台账模块 — Repository 层"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, func, and_, or_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aerial import (
    AerialVehicle, AerialPersonnel, AerialDailyLedger, AerialPersonnelExpense,
    AerialPersonnelWage, AerialVehicleCost, AerialSafetyCheck,
    AerialLedgerAttachment, AerialAttendanceRecord, AerialLedgerSettlement,
    AerialPersonnelAttachment, AerialAgentDraft, AerialVehicleAttachment,
)


class AerialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 高空车档案 ──────────────────────────────────────────────────────────

    async def list_vehicles(self, keyword: str = "", status: str = "", skip: int = 0, limit: int = 20):
        q = select(AerialVehicle).where(AerialVehicle.deleted_at.is_(None))
        if keyword:
            q = q.where(or_(
                AerialVehicle.plate_number.ilike(f"%{keyword}%"),
                AerialVehicle.vehicle_name.ilike(f"%{keyword}%"),
            ))
        if status:
            q = q.where(AerialVehicle.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialVehicle.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_vehicle(self, vehicle_id: uuid.UUID):
        return (await self.db.execute(
            select(AerialVehicle).where(AerialVehicle.id == vehicle_id, AerialVehicle.deleted_at.is_(None))
        )).scalar_one_or_none()

    async def get_vehicle_by_plate(self, plate: str):
        return (await self.db.execute(
            select(AerialVehicle).where(AerialVehicle.plate_number == plate, AerialVehicle.deleted_at.is_(None))
        )).scalar_one_or_none()

    async def list_expiring_vehicles(self, days: int = 30):
        """保险/年检在 N 天内到期或已过期的车辆（未删除）。"""
        from datetime import timedelta
        deadline = datetime.now() + timedelta(days=days)
        q = select(AerialVehicle).where(
            AerialVehicle.deleted_at.is_(None),
            or_(
                and_(
                    AerialVehicle.insurance_expire_date.isnot(None),
                    AerialVehicle.insurance_expire_date <= deadline,
                ),
                and_(
                    AerialVehicle.inspection_expire_date.isnot(None),
                    AerialVehicle.inspection_expire_date <= deadline,
                ),
            ),
        ).order_by(AerialVehicle.plate_number)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_vehicle(self, data: dict):
        obj = AerialVehicle(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_vehicle(self, obj: AerialVehicle, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def soft_delete_vehicle(self, obj: AerialVehicle) -> AerialVehicle:
        obj.deleted_at = datetime.now()
        await self.db.flush()
        return obj

    # ── 人员 ──────────────────────────────────────────────────────────────

    async def list_personnel(self, keyword: str = "", status: str = "", skip: int = 0, limit: int = 20):
        q = select(AerialPersonnel).where(AerialPersonnel.deleted_at.is_(None))
        if keyword:
            q = q.where(or_(
                AerialPersonnel.name.ilike(f"%{keyword}%"),
                AerialPersonnel.phone.ilike(f"%{keyword}%"),
            ))
        if status:
            q = q.where(AerialPersonnel.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialPersonnel.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_personnel(self, personnel_id: uuid.UUID):
        return (await self.db.execute(
            select(AerialPersonnel).where(AerialPersonnel.id == personnel_id, AerialPersonnel.deleted_at.is_(None))
        )).scalar_one_or_none()

    async def create_personnel(self, data: dict):
        obj = AerialPersonnel(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def soft_delete_personnel(self, obj: AerialPersonnel) -> AerialPersonnel:
        obj.deleted_at = datetime.now()
        await self.db.flush()
        return obj

    async def update_personnel(self, obj: AerialPersonnel, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ── 每日台账 ────────────────────────────────────────────────────────────

    async def list_ledgers(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        personnel_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        work_location: Optional[str] = None,
        payment_status: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ):
        # 排序白名单：只允许按这些字段排序（name 为人员姓名，需 join）
        SORTABLE = {
            "ledger_no": AerialDailyLedger.ledger_no,
            "work_date": AerialDailyLedger.work_date,
            "work_location": AerialDailyLedger.work_location,
            "work_content": AerialDailyLedger.work_content,
            "billing_method": AerialDailyLedger.billing_method,
            "quantity": AerialDailyLedger.quantity,
            "receivable_amount": AerialDailyLedger.receivable_amount,
            "received_amount": AerialDailyLedger.received_amount,
            "unpaid_amount": AerialDailyLedger.unpaid_amount,
            "payment_status": AerialDailyLedger.payment_status,
            "name": AerialPersonnel.name,
            "customer_name": AerialDailyLedger.customer_name,
            "contact_phone": AerialDailyLedger.contact_phone,
        }
        q = select(AerialDailyLedger)
        if sort_by == "name":
            q = q.join(AerialPersonnel, AerialPersonnel.id == AerialDailyLedger.personnel_id)
        if date_from:
            q = q.where(AerialDailyLedger.work_date >= datetime.fromisoformat(date_from))
        if date_to:
            q = q.where(AerialDailyLedger.work_date <= datetime.fromisoformat(date_to + "T23:59:59"))
        if personnel_id:
            q = q.where(AerialDailyLedger.personnel_id == uuid.UUID(personnel_id))
        if customer_name:
            q = q.where(AerialDailyLedger.customer_name.ilike(f"%{customer_name}%"))
        if work_location:
            q = q.where(AerialDailyLedger.work_location.ilike(f"%{work_location}%"))
        if payment_status:
            q = q.where(AerialDailyLedger.payment_status == payment_status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        order_col = SORTABLE.get(sort_by)
        if order_col is not None:
            direction = order_col.asc() if sort_order == "asc" else order_col.desc()
            # 加次级排序保证稳定
            q = q.order_by(direction, AerialDailyLedger.work_date.desc(), AerialDailyLedger.created_at.desc())
        else:
            q = q.order_by(AerialDailyLedger.work_date.desc(), AerialDailyLedger.created_at.desc())
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def summarize_ledgers(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        personnel_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        work_location: Optional[str] = None,
        payment_status: Optional[str] = None,
    ) -> dict:
        """对与 list_ledgers 相同的过滤集做聚合求和（合计行数据源）。"""
        q = select(
            func.count(AerialDailyLedger.id).label("trip_count"),
            func.coalesce(func.sum(AerialDailyLedger.quantity), 0).label("quantity"),
            func.coalesce(func.sum(AerialDailyLedger.receivable_amount), 0).label("receivable_amount"),
            func.coalesce(func.sum(AerialDailyLedger.received_amount), 0).label("received_amount"),
            func.coalesce(func.sum(AerialDailyLedger.unpaid_amount), 0).label("unpaid_amount"),
        )
        if date_from:
            q = q.where(AerialDailyLedger.work_date >= datetime.fromisoformat(date_from))
        if date_to:
            q = q.where(AerialDailyLedger.work_date <= datetime.fromisoformat(date_to + "T23:59:59"))
        if personnel_id:
            q = q.where(AerialDailyLedger.personnel_id == uuid.UUID(personnel_id))
        if customer_name:
            q = q.where(AerialDailyLedger.customer_name.ilike(f"%{customer_name}%"))
        if work_location:
            q = q.where(AerialDailyLedger.work_location.ilike(f"%{work_location}%"))
        if payment_status:
            q = q.where(AerialDailyLedger.payment_status == payment_status)
        row = (await self.db.execute(q)).one()
        return {
            "trip_count": row.trip_count,
            "quantity": float(row.quantity),
            "receivable_amount": float(row.receivable_amount),
            "received_amount": float(row.received_amount),
            "unpaid_amount": float(row.unpaid_amount),
        }

    async def list_work_locations(self) -> list[str]:
        """台账中所有去重非空的作业地点，按出现次数降序（筛选下拉框数据源）。"""
        q = select(
            AerialDailyLedger.work_location,
            func.count().label("cnt"),
        ).where(
            AerialDailyLedger.work_location.isnot(None),
            AerialDailyLedger.work_location != "",
        ).group_by(AerialDailyLedger.work_location).order_by(func.count().desc())
        rows = (await self.db.execute(q)).all()
        return [r[0] for r in rows]

    async def get_ledger(self, ledger_id: uuid.UUID):
        return (await self.db.execute(select(AerialDailyLedger).where(AerialDailyLedger.id == ledger_id))).scalar_one_or_none()

    async def create_ledger(self, data: dict):
        obj = AerialDailyLedger(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_ledger(self, obj: AerialDailyLedger, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_ledger(self, obj: AerialDailyLedger):
        """硬删除台账，并清理所有指向它的子表记录（子表外键无级联）。"""
        ledger_id = obj.id
        for model in (
            AerialLedgerAttachment, AerialSafetyCheck, AerialPersonnelExpense,
            AerialPersonnelWage, AerialVehicleCost, AerialLedgerSettlement,
        ):
            await self.db.execute(delete(model).where(model.ledger_id == ledger_id))
        await self.db.execute(
            update(AerialAgentDraft)
            .where(AerialAgentDraft.created_ledger_id == ledger_id)
            .values(created_ledger_id=None)
        )
        await self.db.execute(delete(AerialDailyLedger).where(AerialDailyLedger.id == ledger_id))
        await self.db.flush()

    async def count_ledgers_today(self, dt) -> int:
        from datetime import date as date_type
        target = dt.date() if hasattr(dt, 'date') else dt
        q = select(func.count()).select_from(AerialDailyLedger).where(
            func.date(AerialDailyLedger.work_date) == target
        )
        return (await self.db.execute(q)).scalar() or 0

    # ── 结算流水 ──────────────────────────────────────────────────────────

    async def create_settlement(self, data: dict):
        obj = AerialLedgerSettlement(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def list_settlements(self, ledger_id: uuid.UUID):
        q = (
            select(AerialLedgerSettlement)
            .where(AerialLedgerSettlement.ledger_id == ledger_id)
            .order_by(AerialLedgerSettlement.created_at.asc())
        )
        return (await self.db.execute(q)).scalars().all()

    async def get_settlement(self, settlement_id: uuid.UUID):
        return (await self.db.execute(
            select(AerialLedgerSettlement).where(AerialLedgerSettlement.id == settlement_id)
        )).scalar_one_or_none()

    async def delete_settlement(self, obj):
        await self.db.delete(obj)
        await self.db.flush()
        return obj

    async def sum_settlements(self, ledger_id: uuid.UUID) -> float:
        """台账下全部结算流水金额之和（与实收一致）。"""
        q = select(func.coalesce(func.sum(AerialLedgerSettlement.amount), 0)).where(
            AerialLedgerSettlement.ledger_id == ledger_id
        )
        return float((await self.db.execute(q)).scalar())

    async def last_settlement(self, ledger_id: uuid.UUID):
        """最近登记的一条结算流水。"""
        q = (
            select(AerialLedgerSettlement)
            .where(AerialLedgerSettlement.ledger_id == ledger_id)
            .order_by(AerialLedgerSettlement.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    # ── 人员垫付 ──────────────────────────────────────────────────────────

    async def list_expenses(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        personnel_id: Optional[str] = None,
        expense_type: Optional[str] = None,
        reimbursement_status: Optional[str] = None,
        ledger_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        q = select(AerialPersonnelExpense)
        if date_from:
            q = q.where(AerialPersonnelExpense.expense_date >= date_from)
        if date_to:
            q = q.where(AerialPersonnelExpense.expense_date <= date_to + " 23:59:59")
        if personnel_id:
            q = q.where(AerialPersonnelExpense.personnel_id == uuid.UUID(personnel_id))
        if expense_type:
            q = q.where(AerialPersonnelExpense.expense_type == expense_type)
        if reimbursement_status:
            q = q.where(AerialPersonnelExpense.reimbursement_status == reimbursement_status)
        if ledger_id:
            q = q.where(AerialPersonnelExpense.ledger_id == uuid.UUID(ledger_id))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialPersonnelExpense.expense_date.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_expense(self, expense_id: uuid.UUID):
        return (await self.db.execute(select(AerialPersonnelExpense).where(AerialPersonnelExpense.id == expense_id))).scalar_one_or_none()

    async def create_expense(self, data: dict):
        obj = AerialPersonnelExpense(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_expense(self, obj: AerialPersonnelExpense, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ── 人员工资 ──────────────────────────────────────────────────────────

    async def list_wages(
        self,
        wage_month: Optional[str] = None,
        personnel_id: Optional[str] = None,
        payment_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        q = select(AerialPersonnelWage)
        if wage_month:
            q = q.where(AerialPersonnelWage.wage_month == wage_month)
        if personnel_id:
            q = q.where(AerialPersonnelWage.personnel_id == uuid.UUID(personnel_id))
        if payment_status:
            q = q.where(AerialPersonnelWage.payment_status == payment_status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialPersonnelWage.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_wage(self, wage_id: uuid.UUID):
        return (await self.db.execute(select(AerialPersonnelWage).where(AerialPersonnelWage.id == wage_id))).scalar_one_or_none()

    async def create_wage(self, data: dict):
        obj = AerialPersonnelWage(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_wage(self, obj: AerialPersonnelWage, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ── 车辆费用 ────────────────────────────────────────────────────────────

    async def list_costs(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        cost_type: Optional[str] = None,
        aerial_vehicle_id: Optional[str] = None,
        ledger_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        q = select(AerialVehicleCost)
        if date_from:
            q = q.where(AerialVehicleCost.cost_date >= date_from)
        if date_to:
            q = q.where(AerialVehicleCost.cost_date <= date_to + " 23:59:59")
        if cost_type:
            q = q.where(AerialVehicleCost.cost_type == cost_type)
        if aerial_vehicle_id:
            q = q.where(AerialVehicleCost.aerial_vehicle_id == uuid.UUID(aerial_vehicle_id))
        if ledger_id:
            q = q.where(AerialVehicleCost.ledger_id == uuid.UUID(ledger_id))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialVehicleCost.cost_date.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_cost(self, cost_id: uuid.UUID):
        return (await self.db.execute(select(AerialVehicleCost).where(AerialVehicleCost.id == cost_id))).scalar_one_or_none()

    async def create_cost(self, data: dict):
        obj = AerialVehicleCost(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_cost(self, obj: AerialVehicleCost, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_cost(self, obj: AerialVehicleCost):
        await self.db.delete(obj)
        await self.db.flush()
        return obj

    # ── 安全检查 ────────────────────────────────────────────────────────────

    async def list_safety_checks(self, ledger_id: str, check_type: Optional[str] = None):
        q = select(AerialSafetyCheck).where(AerialSafetyCheck.ledger_id == uuid.UUID(ledger_id))
        if check_type:
            q = q.where(AerialSafetyCheck.check_type == check_type)
        q = q.order_by(AerialSafetyCheck.created_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_safety_check(self, data: dict):
        obj = AerialSafetyCheck(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ── 附件 ────────────────────────────────────────────────────────────────

    async def list_attachments(self, ledger_id: str, attachment_type: Optional[str] = None):
        q = select(AerialLedgerAttachment).where(AerialLedgerAttachment.ledger_id == uuid.UUID(ledger_id))
        if attachment_type:
            q = q.where(AerialLedgerAttachment.attachment_type == attachment_type)
        q = q.order_by(AerialLedgerAttachment.uploaded_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_attachment(self, data: dict):
        obj = AerialLedgerAttachment(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_attachment(self, attachment_id: uuid.UUID):
        obj = (await self.db.execute(select(AerialLedgerAttachment).where(AerialLedgerAttachment.id == attachment_id))).scalar_one_or_none()
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
        return obj

    # ── 报表统计 ────────────────────────────────────────────────────────────

    async def get_daily_summary(self, date_str: str):
        """获取某日汇总"""
        from datetime import date as date_type
        dt = date_type.fromisoformat(date_str)
        base = func.date(AerialDailyLedger.work_date) == dt
        q = select(
            func.count(AerialDailyLedger.id).label("trip_count"),
            func.coalesce(func.sum(AerialDailyLedger.receivable_amount), 0).label("receivable"),
            func.coalesce(func.sum(AerialDailyLedger.received_amount), 0).label("received"),
            func.coalesce(func.sum(AerialDailyLedger.unpaid_amount), 0).label("unpaid"),
            func.coalesce(func.sum(AerialDailyLedger.personnel_wage_amount), 0).label("wages"),
            func.coalesce(func.sum(AerialDailyLedger.reimbursement_amount), 0).label("reimbursements"),
            func.coalesce(func.sum(AerialDailyLedger.vehicle_direct_cost), 0).label("vehicle_costs"),
            func.coalesce(func.sum(AerialDailyLedger.gross_profit), 0).label("gross_profit"),
        ).where(base)
        row = (await self.db.execute(q)).one()
        return {
            "trip_count": row.trip_count,
            "receivable": float(row.receivable),
            "received": float(row.received),
            "unpaid": float(row.unpaid),
            "wages": float(row.wages),
            "reimbursements": float(row.reimbursements),
            "vehicle_costs": float(row.vehicle_costs),
            "gross_profit": float(row.gross_profit),
        }

    async def get_monthly_summary(self, year_month: str):
        """获取某月汇总"""
        base = func.to_char(AerialDailyLedger.work_date, 'YYYY-MM') == year_month
        q = select(
            func.count(AerialDailyLedger.id).label("trip_count"),
            func.count(func.distinct(func.date(AerialDailyLedger.work_date))).label("work_days"),
            func.coalesce(func.sum(AerialDailyLedger.receivable_amount), 0).label("receivable"),
            func.coalesce(func.sum(AerialDailyLedger.received_amount), 0).label("received"),
            func.coalesce(func.sum(AerialDailyLedger.unpaid_amount), 0).label("unpaid"),
            func.coalesce(func.sum(AerialDailyLedger.personnel_wage_amount), 0).label("wages"),
            func.coalesce(func.sum(AerialDailyLedger.reimbursement_amount), 0).label("reimbursements"),
            func.coalesce(func.sum(AerialDailyLedger.vehicle_direct_cost), 0).label("vehicle_costs"),
            func.coalesce(func.sum(AerialDailyLedger.gross_profit), 0).label("gross_profit"),
            func.coalesce(func.sum(AerialDailyLedger.estimated_profit), 0).label("estimated_profit"),
        ).where(base)
        row = (await self.db.execute(q)).one()
        return {
            "trip_count": row.trip_count,
            "work_days": row.work_days,
            "receivable": float(row.receivable),
            "received": float(row.received),
            "unpaid": float(row.unpaid),
            "wages": float(row.wages),
            "reimbursements": float(row.reimbursements),
            "vehicle_costs": float(row.vehicle_costs),
            "gross_profit": float(row.gross_profit),
            "estimated_profit": float(row.estimated_profit),
        }

    async def get_unpaid_ledgers(self, skip: int = 0, limit: int = 20):
        q = select(AerialDailyLedger).where(
            and_(
                AerialDailyLedger.unpaid_amount > 0,
                AerialDailyLedger.payment_status.notin_(["free", "included_in_order"]),
            )
        ).order_by(AerialDailyLedger.work_date.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_pending_reimbursements(self, skip: int = 0, limit: int = 20):
        q = select(AerialPersonnelExpense).where(
            AerialPersonnelExpense.reimbursement_status == "pending_reimbursement"
        ).order_by(AerialPersonnelExpense.expense_date.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_cost_by_type(self, year_month: Optional[str] = None):
        """费用分类汇总（创建即登记，全部费用计入，与台账 vehicle_direct_cost 口径一致）"""
        q = select(
            AerialVehicleCost.cost_type,
            func.coalesce(func.sum(AerialVehicleCost.amount), 0).label("total"),
        )
        if year_month:
            q = q.where(func.to_char(AerialVehicleCost.cost_date, 'YYYY-MM') == year_month)
        q = q.group_by(AerialVehicleCost.cost_type)
        rows = (await self.db.execute(q)).all()
        return [{"cost_type": r[0], "total": float(r[1])} for r in rows]

    async def get_personnel_summary(self, year_month: str):
        """人员工资月度汇总"""
        base = func.to_char(AerialDailyLedger.work_date, 'YYYY-MM') == year_month
        q = select(
            AerialDailyLedger.personnel_id,
            AerialPersonnel.name,
            func.count(AerialDailyLedger.id).label("trip_count"),
            func.coalesce(func.sum(AerialDailyLedger.receivable_amount), 0).label("receivable"),
            func.coalesce(func.sum(AerialDailyLedger.received_amount), 0).label("received"),
            func.coalesce(func.sum(AerialDailyLedger.personnel_wage_amount), 0).label("wages"),
        ).join(
            AerialPersonnel, AerialDailyLedger.personnel_id == AerialPersonnel.id
        ).where(base).group_by(
            AerialDailyLedger.personnel_id, AerialPersonnel.name
        )
        rows = (await self.db.execute(q)).all()
        return [
            {
                "personnel_id": str(r[0]),
                "name": r[1],
                "trip_count": r[2],
                "receivable": float(r[3]),
                "received": float(r[4]),
                "wages": float(r[5]),
            }
            for r in rows
        ]

    # ── 高空作业考勤 ─────────────────────────────────────────────────────────

    async def list_attendance(
        self,
        target_type: Optional[str] = None,
        vehicle_id: Optional[str] = None,
        personnel_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 1000,
    ):
        q = select(AerialAttendanceRecord)
        if target_type:
            q = q.where(AerialAttendanceRecord.target_type == target_type)
        if vehicle_id:
            q = q.where(AerialAttendanceRecord.vehicle_id == uuid.UUID(vehicle_id))
        if personnel_id:
            q = q.where(AerialAttendanceRecord.personnel_id == uuid.UUID(personnel_id))
        if date_from:
            q = q.where(AerialAttendanceRecord.att_date >= datetime.fromisoformat(date_from).date())
        if date_to:
            q = q.where(AerialAttendanceRecord.att_date <= datetime.fromisoformat(date_to).date())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialAttendanceRecord.att_date.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_attendance(self, attendance_id: uuid.UUID):
        return (await self.db.execute(
            select(AerialAttendanceRecord).where(AerialAttendanceRecord.id == attendance_id)
        )).scalar_one_or_none()

    async def get_attendance_by_key(self, target_type: str, entity_id: uuid.UUID, att_date: date):
        q = select(AerialAttendanceRecord).where(
            AerialAttendanceRecord.target_type == target_type,
            AerialAttendanceRecord.att_date == att_date,
        )
        if target_type == "vehicle":
            q = q.where(AerialAttendanceRecord.vehicle_id == entity_id)
        else:
            q = q.where(AerialAttendanceRecord.personnel_id == entity_id)
        return (await self.db.execute(q)).scalar_one_or_none()

    async def create_attendance(self, data: dict):
        obj = AerialAttendanceRecord(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_attendance(self, obj: AerialAttendanceRecord, data: dict):
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_attendance(self, obj: AerialAttendanceRecord):
        await self.db.delete(obj)
        await self.db.flush()
        return obj

    # ── 人员附件 ─────────────────────────────────────────────────────────────

    async def list_personnel_attachments(self, personnel_id: str, attachment_type: Optional[str] = None):
        q = select(AerialPersonnelAttachment).where(AerialPersonnelAttachment.personnel_id == uuid.UUID(personnel_id))
        if attachment_type:
            q = q.where(AerialPersonnelAttachment.attachment_type == attachment_type)
        q = q.order_by(AerialPersonnelAttachment.uploaded_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_personnel_attachment(self, data: dict):
        obj = AerialPersonnelAttachment(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_personnel_attachment(self, attachment_id: uuid.UUID):
        obj = (await self.db.execute(
            select(AerialPersonnelAttachment).where(AerialPersonnelAttachment.id == attachment_id)
        )).scalar_one_or_none()
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
        return obj

    # ── 车辆附件 ─────────────────────────────────────────────────────────────

    async def list_vehicle_attachments(self, vehicle_id: str, attachment_type: Optional[str] = None):
        q = select(AerialVehicleAttachment).where(AerialVehicleAttachment.vehicle_id == uuid.UUID(vehicle_id))
        if attachment_type:
            q = q.where(AerialVehicleAttachment.attachment_type == attachment_type)
        q = q.order_by(AerialVehicleAttachment.uploaded_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_vehicle_attachment(self, data: dict):
        obj = AerialVehicleAttachment(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_vehicle_attachment(self, attachment_id: uuid.UUID):
        obj = (await self.db.execute(
            select(AerialVehicleAttachment).where(AerialVehicleAttachment.id == attachment_id)
        )).scalar_one_or_none()
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
        return obj
