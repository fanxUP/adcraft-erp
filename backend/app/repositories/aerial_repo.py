"""高空作业车台账模块 — Repository 层"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aerial import (
    AerialVehicle, AerialPersonnel, AerialDailyLedger, AerialPersonnelExpense,
    AerialPersonnelWage, AerialVehicleCost, AerialSafetyCheck,
    AerialLedgerAttachment, AerialLedgerAuditLog,
)


class AerialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 高空车档案 ──────────────────────────────────────────────────────────

    async def list_vehicles(self, keyword: str = "", status: str = "", skip: int = 0, limit: int = 20):
        q = select(AerialVehicle)
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
        return (await self.db.execute(select(AerialVehicle).where(AerialVehicle.id == vehicle_id))).scalar_one_or_none()

    async def get_vehicle_by_plate(self, plate: str):
        return (await self.db.execute(select(AerialVehicle).where(AerialVehicle.plate_number == plate))).scalar_one_or_none()

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
        audit_status: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        q = select(AerialDailyLedger)
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
        if audit_status:
            q = q.where(AerialDailyLedger.audit_status == audit_status)
        if status:
            q = q.where(AerialDailyLedger.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialDailyLedger.work_date.desc(), AerialDailyLedger.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

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

    async def count_ledgers_today(self, dt) -> int:
        from datetime import date as date_type
        target = dt.date() if hasattr(dt, 'date') else dt
        q = select(func.count()).select_from(AerialDailyLedger).where(
            and_(
                func.date(AerialDailyLedger.work_date) == target,
                AerialDailyLedger.status != "cancelled",
            )
        )
        return (await self.db.execute(q)).scalar() or 0

    # ── 人员垫付 ──────────────────────────────────────────────────────────

    async def list_expenses(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        personnel_id: Optional[str] = None,
        expense_type: Optional[str] = None,
        review_status: Optional[str] = None,
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
        if review_status:
            q = q.where(AerialPersonnelExpense.review_status == review_status)
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
        review_status: Optional[str] = None,
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
        if review_status:
            q = q.where(AerialVehicleCost.review_status == review_status)
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

    # ── 审计日志 ────────────────────────────────────────────────────────────

    async def list_audit_logs(self, ledger_id: Optional[str] = None, skip: int = 0, limit: int = 50):
        q = select(AerialLedgerAuditLog)
        if ledger_id:
            q = q.where(AerialLedgerAuditLog.ledger_id == uuid.UUID(ledger_id))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialLedgerAuditLog.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def create_audit_log(self, data: dict):
        obj = AerialLedgerAuditLog(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    # ── 报表统计 ────────────────────────────────────────────────────────────

    async def get_daily_summary(self, date_str: str):
        """获取某日汇总"""
        from datetime import date as date_type
        dt = date_type.fromisoformat(date_str)
        base = and_(
            func.date(AerialDailyLedger.work_date) == dt,
            AerialDailyLedger.status != "cancelled",
        )
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
        base = and_(
            func.to_char(AerialDailyLedger.work_date, 'YYYY-MM') == year_month,
            AerialDailyLedger.status != "cancelled",
        )
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
                AerialDailyLedger.status.notin_(["cancelled"]),
                AerialDailyLedger.payment_status.notin_(["free", "included_in_order"]),
            )
        ).order_by(AerialDailyLedger.work_date.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_pending_expenses(self, skip: int = 0, limit: int = 20):
        q = select(AerialPersonnelExpense).where(
            AerialPersonnelExpense.review_status == "pending"
        ).order_by(AerialPersonnelExpense.expense_date.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_pending_reimbursements(self, skip: int = 0, limit: int = 20):
        q = select(AerialPersonnelExpense).where(
            and_(
                AerialPersonnelExpense.review_status == "approved",
                AerialPersonnelExpense.reimbursement_status == "pending_reimbursement",
            )
        ).order_by(AerialPersonnelExpense.expense_date.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    async def get_cost_by_type(self, year_month: Optional[str] = None):
        base = AerialVehicleCost.review_status == "approved"
        if year_month:
            base = and_(base, func.to_char(AerialVehicleCost.cost_date, 'YYYY-MM') == year_month)
        q = select(
            AerialVehicleCost.cost_type,
            func.coalesce(func.sum(AerialVehicleCost.amount), 0).label("total"),
        ).where(base).group_by(AerialVehicleCost.cost_type)
        rows = (await self.db.execute(q)).all()
        return [{"cost_type": r[0], "total": float(r[1])} for r in rows]

    async def get_personnel_summary(self, year_month: str):
        """人员工资月度汇总"""
        base = and_(
            func.to_char(AerialDailyLedger.work_date, 'YYYY-MM') == year_month,
            AerialDailyLedger.status != "cancelled",
        )
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
