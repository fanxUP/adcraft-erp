"""高空作业车台账模块 — Service 层"""

import json
import random
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aerial import AerialDailyLedger
from app.repositories.aerial_repo import AerialRepository


# 审计日志动作常量
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_VOID = "void"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_REVIEW = "review"
ACTION_REIMBURSE = "reimburse"
ACTION_PAY_WAGE = "pay_wage"
ACTION_RECORD_PAYMENT = "record_payment"


class AerialService:
    def __init__(self, db: AsyncSession, current_user=None, ip_address: str = ""):
        self.db = db
        self.current_user = current_user
        self.ip_address = ip_address
        self.repo = AerialRepository(db)

    def _user_id(self):
        return self.current_user.id if self.current_user else None

    def _log(self, ledger_id, action, target_type=None, target_id=None, before=None, after=None, remark=None):
        return self.repo.create_audit_log({
            "ledger_id": ledger_id,
            "operator_id": self._user_id(),
            "action": action,
            "source": "erp",
            "target_type": target_type,
            "target_id": target_id,
            "before_json": json.dumps(before, ensure_ascii=False, default=str) if before else None,
            "after_json": json.dumps(after, ensure_ascii=False, default=str) if after else None,
            "remark": remark,
        })

    # ── 高空车档案 ──────────────────────────────────────────────────────────

    async def list_vehicles(self, keyword="", status="", page=1, page_size=20):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_vehicles(keyword, status, skip, page_size)
        return [self._vehicle_to_dict(v) for v in items], total

    async def get_vehicle(self, vehicle_id: str):
        obj = await self.repo.get_vehicle(uuid.UUID(vehicle_id))
        if not obj:
            raise ValueError("高空车不存在")
        return self._vehicle_to_dict(obj)

    async def create_vehicle(self, data: dict):
        plate = data.get("plate_number", "").strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        existing = await self.repo.get_vehicle_by_plate(plate)
        if existing:
            raise ValueError(f"车牌号 {plate} 已存在")
        if data.get("default_personnel_id"):
            data["default_personnel_id"] = uuid.UUID(data["default_personnel_id"])
        if data.get("purchase_date"):
            data["purchase_date"] = datetime.fromisoformat(data["purchase_date"])
        if data.get("insurance_expire_date"):
            data["insurance_expire_date"] = datetime.fromisoformat(data["insurance_expire_date"])
        if data.get("inspection_expire_date"):
            data["inspection_expire_date"] = datetime.fromisoformat(data["inspection_expire_date"])
        if data.get("maintenance_due_date"):
            data["maintenance_due_date"] = datetime.fromisoformat(data["maintenance_due_date"])
        obj = await self.repo.create_vehicle(data)
        result = self._vehicle_to_dict(obj)
        await self._log(None, ACTION_CREATE, target_type="vehicle", target_id=obj.id, after=result)
        return result

    async def update_vehicle(self, vehicle_id: str, data: dict):
        obj = await self.repo.get_vehicle(uuid.UUID(vehicle_id))
        if not obj:
            raise ValueError("高空车不存在")
        before = self._vehicle_to_dict(obj)
        if "plate_number" in data and data["plate_number"] != obj.plate_number:
            existing = await self.repo.get_vehicle_by_plate(data["plate_number"])
            if existing:
                raise ValueError(f"车牌号 {data['plate_number']} 已存在")
        for k in ["default_personnel_id"]:
            if data.get(k):
                data[k] = uuid.UUID(data[k])
        for k in ["purchase_date", "insurance_expire_date", "inspection_expire_date", "maintenance_due_date"]:
            if data.get(k):
                data[k] = datetime.fromisoformat(data[k])
        obj = await self.repo.update_vehicle(obj, data)
        after = self._vehicle_to_dict(obj)
        await self._log(None, ACTION_UPDATE, target_type="vehicle", target_id=obj.id, before=before, after=after)
        return after

    def _vehicle_to_dict(self, v):
        return {
            "id": str(v.id),
            "plate_number": v.plate_number,
            "vehicle_name": v.vehicle_name,
            "brand_model": v.brand_model,
            "max_working_height": v.max_working_height,
            "platform_capacity": v.platform_capacity,
            "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
            "status": v.status,
            "default_personnel_id": str(v.default_personnel_id) if v.default_personnel_id else None,
            "default_personnel_name": v.default_personnel.name if v.default_personnel else None,
            "insurance_expire_date": v.insurance_expire_date.isoformat() if v.insurance_expire_date else None,
            "inspection_expire_date": v.inspection_expire_date.isoformat() if v.inspection_expire_date else None,
            "maintenance_due_date": v.maintenance_due_date.isoformat() if v.maintenance_due_date else None,
            "remark": v.remark,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }

    # ── 人员 ──────────────────────────────────────────────────────────────

    async def list_personnel(self, keyword="", status="", page=1, page_size=20):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_personnel(keyword, status, skip, page_size)
        return [self._personnel_to_dict(d) for d in items], total

    async def get_personnel(self, personnel_id: str):
        obj = await self.repo.get_personnel(uuid.UUID(personnel_id))
        if not obj:
            raise ValueError("人员不存在")
        return self._personnel_to_dict(obj)

    async def create_personnel(self, data: dict):
        if not data.get("name", "").strip():
            raise ValueError("人员姓名不能为空")
        if data.get("license_expire_date"):
            data["license_expire_date"] = datetime.fromisoformat(data["license_expire_date"])
        obj = await self.repo.create_personnel(data)
        result = self._personnel_to_dict(obj)
        await self._log(None, ACTION_CREATE, target_type="personnel", target_id=obj.id, after=result)
        return result

    async def update_personnel(self, personnel_id: str, data: dict):
        obj = await self.repo.get_personnel(uuid.UUID(personnel_id))
        if not obj:
            raise ValueError("人员不存在")
        before = self._personnel_to_dict(obj)
        if data.get("license_expire_date"):
            data["license_expire_date"] = datetime.fromisoformat(data["license_expire_date"])
        obj = await self.repo.update_personnel(obj, data)
        after = self._personnel_to_dict(obj)
        await self._log(None, ACTION_UPDATE, target_type="personnel", target_id=obj.id, before=before, after=after)
        return after

    def _personnel_to_dict(self, d):
        return {
            "id": str(d.id),
            "name": d.name,
            "phone": d.phone,
            "license_no": d.license_no,
            "license_type": d.license_type,
            "license_expire_date": d.license_expire_date.isoformat() if d.license_expire_date else None,
            "is_external": d.is_external,
            "status": d.status,
            "remark": d.remark,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }

    # ── 每日台账 ────────────────────────────────────────────────────────────

    async def list_ledgers(self, page=1, page_size=20, **filters):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_ledgers(skip=skip, limit=page_size, **filters)
        return [self._ledger_to_dict(l) for l in items], total

    async def get_ledger(self, ledger_id: str):
        obj = await self.repo.get_ledger(uuid.UUID(ledger_id))
        if not obj:
            raise ValueError("台账不存在")
        return self._ledger_to_dict_detail(obj)

    async def create_ledger(self, data: dict):
        # 必填校验
        if not data.get("work_date"):
            raise ValueError("出车日期不能为空")
        if not data.get("aerial_vehicle_id"):
            raise ValueError("高空车不能为空")
        if not data.get("personnel_id"):
            raise ValueError("人员不能为空")
        if not data.get("work_location", "").strip():
            raise ValueError("作业地点不能为空")

        # 转换类型
        data["aerial_vehicle_id"] = uuid.UUID(data["aerial_vehicle_id"])
        data["personnel_id"] = uuid.UUID(data["personnel_id"])
        data["work_date"] = datetime.fromisoformat(data["work_date"]) if isinstance(data["work_date"], str) else data["work_date"]

        for k in ["planned_start_time", "planned_end_time", "actual_start_time", "actual_end_time", "payment_time"]:
            if data.get(k) and isinstance(data[k], str):
                data[k] = datetime.fromisoformat(data[k])

        # 冗余车牌号
        vehicle = await self.repo.get_vehicle(data["aerial_vehicle_id"])
        if vehicle:
            data["plate_number"] = vehicle.plate_number

        # 计算金额
        data = self._calc_amounts(data)

        # 设置创建人
        data["created_by"] = self._user_id()

        # 自动生成台账编号（带重试机制防止并发重复）
        today_str = date.today().strftime("%Y%m%d")
        count = await self.repo.count_ledgers_today(date.today())
        max_retries = 5
        obj = None
        for attempt in range(max_retries):
            if attempt == 0:
                data["ledger_no"] = f"GT-{today_str}-{count + 1:03d}"
            else:
                # 并发冲突时加随机后缀
                suffix = random.randint(100, 999)
                data["ledger_no"] = f"GT-{today_str}-{count + 1 + attempt:03d}-{suffix}"
            try:
                obj = await self.repo.create_ledger(data)
                break
            except IntegrityError:
                await self.db.rollback()
                if attempt == max_retries - 1:
                    raise ValueError("台账编号生成失败，请稍后重试")

        # 审计日志
        await self._log(obj.id, ACTION_CREATE, "ledger", obj.id, after=self._ledger_to_dict(obj))

        return self._ledger_to_dict(obj)

    async def update_ledger(self, ledger_id: str, data: dict):
        obj = await self.repo.get_ledger(uuid.UUID(ledger_id))
        if not obj:
            raise ValueError("台账不存在")
        if obj.status == "cancelled":
            raise ValueError("已作废台账不能编辑")

        # 转换类型
        for k in ["aerial_vehicle_id", "personnel_id"]:
            if data.get(k):
                data[k] = uuid.UUID(data[k])
        for k in ["work_date", "planned_start_time", "planned_end_time", "actual_start_time", "actual_end_time", "payment_time"]:
            if data.get(k) and isinstance(data[k], str):
                data[k] = datetime.fromisoformat(data[k])

        # 如果改了车辆，更新冗余车牌号
        if "aerial_vehicle_id" in data:
            vehicle = await self.repo.get_vehicle(data["aerial_vehicle_id"])
            if vehicle:
                data["plate_number"] = vehicle.plate_number

        before = self._ledger_to_dict(obj)

        # 重新计算金额
        merged = {**before, **{k: v for k, v in data.items() if v is not None}}
        data = {**data, **self._calc_amounts(merged)}

        obj = await self.repo.update_ledger(obj, data)

        # 审计日志
        await self._log(obj.id, ACTION_UPDATE, "ledger", obj.id, before=before, after=self._ledger_to_dict(obj))

        return self._ledger_to_dict(obj)

    async def void_ledger(self, ledger_id: str, reason: str):
        obj = await self.repo.get_ledger(uuid.UUID(ledger_id))
        if not obj:
            raise ValueError("台账不存在")
        if obj.status == "cancelled":
            raise ValueError("台账已作废")

        before = self._ledger_to_dict(obj)
        obj = await self.repo.update_ledger(obj, {
            "status": "cancelled",
            "voided_by": self._user_id(),
            "voided_at": datetime.now(),
            "void_reason": reason,
        })

        await self._log(obj.id, ACTION_VOID, "ledger", obj.id, before=before, after=self._ledger_to_dict(obj), remark=reason)
        return self._ledger_to_dict(obj)

    async def approve_ledger(self, ledger_id: str, remark: str = ""):
        obj = await self.repo.get_ledger(uuid.UUID(ledger_id))
        if not obj:
            raise ValueError("台账不存在")
        before = self._ledger_to_dict(obj)
        obj = await self.repo.update_ledger(obj, {
            "audit_status": "approved",
            "status": "reviewed",
            "reviewed_by": self._user_id(),
            "reviewed_at": datetime.now(),
        })
        await self._log(obj.id, ACTION_APPROVE, "ledger", obj.id, before=before, after=self._ledger_to_dict(obj), remark=remark)
        return self._ledger_to_dict(obj)

    async def reject_ledger(self, ledger_id: str, remark: str = ""):
        obj = await self.repo.get_ledger(uuid.UUID(ledger_id))
        if not obj:
            raise ValueError("台账不存在")
        before = self._ledger_to_dict(obj)
        obj = await self.repo.update_ledger(obj, {
            "audit_status": "rejected",
            "reviewed_by": self._user_id(),
            "reviewed_at": datetime.now(),
        })
        await self._log(obj.id, ACTION_REJECT, "ledger", obj.id, before=before, after=self._ledger_to_dict(obj), remark=remark)
        return self._ledger_to_dict(obj)

    def _calc_amounts(self, data: dict) -> dict:
        receivable = float(data.get("receivable_amount", 0) or 0)
        discount = float(data.get("discount_amount", 0) or 0)
        final = data.get("final_amount")
        if final is None:
            final = receivable - discount
        else:
            final = float(final)
        received = float(data.get("received_amount", 0) or 0)
        unpaid = final - received
        wage = float(data.get("personnel_wage_amount", 0) or 0)
        reimbursement = float(data.get("reimbursement_amount", 0) or 0)
        vehicle_cost = float(data.get("vehicle_direct_cost", 0) or 0)

        data["receivable_amount"] = receivable
        data["discount_amount"] = discount
        data["final_amount"] = final
        data["received_amount"] = received
        data["unpaid_amount"] = max(0, unpaid)
        data["gross_profit"] = received - wage - reimbursement - vehicle_cost
        data["estimated_profit"] = final - wage - reimbursement - vehicle_cost

        # 里程
        start = data.get("start_mileage")
        end = data.get("end_mileage")
        if start is not None and end is not None:
            data["distance_km"] = float(end) - float(start)

        # 收款状态自动判断
        if received >= final and final > 0:
            data["payment_status"] = "paid"
        elif received > 0:
            data["payment_status"] = "partial"
        elif data.get("payment_status") not in ("credit", "free", "included_in_order"):
            data["payment_status"] = "unpaid"

        return data

    def _ledger_to_dict(self, l):
        return {
            "id": str(l.id),
            "ledger_no": l.ledger_no,
            "work_date": l.work_date.strftime("%Y-%m-%d") if l.work_date else None,
            "aerial_vehicle_id": str(l.aerial_vehicle_id),
            "plate_number": l.plate_number,
            "personnel_id": str(l.personnel_id),
            "name": l.personnel.name if l.personnel else None,
            "assistant_names": l.assistant_names,
            "customer_name": l.customer_name,
            "contact_name": l.contact_name,
            "contact_phone": l.contact_phone,
            "related_order_no": l.related_order_no,
            "related_task_no": l.related_task_no,
            "work_location": l.work_location,
            "work_type": l.work_type,
            "work_content": l.work_content,
            "billing_method": l.billing_method,
            "unit_price": float(l.unit_price),
            "quantity": float(l.quantity),
            "receivable_amount": float(l.receivable_amount),
            "discount_amount": float(l.discount_amount),
            "final_amount": float(l.final_amount),
            "received_amount": float(l.received_amount),
            "unpaid_amount": float(l.unpaid_amount),
            "settlement_type": l.settlement_type,
            "payment_status": l.payment_status,
            "payment_method": l.payment_method,
            "payment_time": l.payment_time.isoformat() if l.payment_time else None,
            "personnel_wage_amount": float(l.personnel_wage_amount),
            "reimbursement_amount": float(l.reimbursement_amount),
            "vehicle_direct_cost": float(l.vehicle_direct_cost),
            "gross_profit": float(l.gross_profit),
            "estimated_profit": float(l.estimated_profit),
            "abnormal_flag": l.abnormal_flag,
            "abnormal_description": l.abnormal_description,
            "status": l.status,
            "audit_status": l.audit_status,
            "void_reason": l.void_reason,
            "remark": l.remark,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }

    def _ledger_to_dict_detail(self, l):
        d = self._ledger_to_dict(l)
        d.update({
            "planned_start_time": l.planned_start_time.isoformat() if l.planned_start_time else None,
            "planned_end_time": l.planned_end_time.isoformat() if l.planned_end_time else None,
            "actual_start_time": l.actual_start_time.isoformat() if l.actual_start_time else None,
            "actual_end_time": l.actual_end_time.isoformat() if l.actual_end_time else None,
            "start_mileage": float(l.start_mileage) if l.start_mileage else None,
            "end_mileage": float(l.end_mileage) if l.end_mileage else None,
            "distance_km": float(l.distance_km) if l.distance_km else None,
            "invoice_required": l.invoice_required,
            "invoice_status": l.invoice_status,
            "created_by": str(l.created_by) if l.created_by else None,
            "reviewed_by": str(l.reviewed_by) if l.reviewed_by else None,
            "reviewed_at": l.reviewed_at.isoformat() if l.reviewed_at else None,
            "voided_by": str(l.voided_by) if l.voided_by else None,
            "voided_at": l.voided_at.isoformat() if l.voided_at else None,
        })
        return d

    # ── 人员垫付 ──────────────────────────────────────────────────────────

    async def list_expenses(self, page=1, page_size=20, **filters):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_expenses(skip=skip, limit=page_size, **filters)
        return [self._expense_to_dict(e) for e in items], total

    async def create_expense(self, data: dict):
        if not data.get("ledger_id"):
            raise ValueError("关联台账不能为空")
        if float(data.get("amount", 0)) <= 0:
            raise ValueError("金额必须大于 0")

        data["ledger_id"] = uuid.UUID(data["ledger_id"])
        data["personnel_id"] = uuid.UUID(data["personnel_id"])
        data["expense_date"] = datetime.fromisoformat(data["expense_date"]) if isinstance(data.get("expense_date"), str) else data.get("expense_date", datetime.now())

        # 校验台账存在
        ledger = await self.repo.get_ledger(data["ledger_id"])
        if not ledger:
            raise ValueError("关联台账不存在")

        obj = await self.repo.create_expense(data)
        await self._log(data["ledger_id"], ACTION_CREATE, "expense", obj.id, after=self._expense_to_dict(obj))
        return self._expense_to_dict(obj)

    async def review_expense(self, expense_id: str, status: str, remark: str = ""):
        obj = await self.repo.get_expense(uuid.UUID(expense_id))
        if not obj:
            raise ValueError("垫付记录不存在")
        if obj.review_status != "pending":
            raise ValueError("只能审核待审核状态的记录")

        before = self._expense_to_dict(obj)
        update_data = {
            "review_status": status,
            "reviewed_by": self._user_id(),
            "reviewed_at": datetime.now(),
        }
        if status == "approved":
            update_data["reimbursement_status"] = "pending_reimbursement"

        obj = await self.repo.update_expense(obj, update_data)

        # 更新台账报销金额（重新汇总所有已审核费用，避免重复累加）
        if status == "approved" and obj.ledger_id:
            ledger = await self.repo.get_ledger(obj.ledger_id)
            if ledger:
                total_reimbursed = await self._sum_expenses_for_ledger(obj.ledger_id)
                await self.repo.update_ledger(ledger, {"reimbursement_amount": total_reimbursed})

        await self._log(obj.ledger_id, ACTION_REVIEW, "expense", obj.id, before=before, after=self._expense_to_dict(obj), remark=remark)
        return self._expense_to_dict(obj)

    async def reimburse_expense(self, expense_id: str, remark: str = ""):
        obj = await self.repo.get_expense(uuid.UUID(expense_id))
        if not obj:
            raise ValueError("垫付记录不存在")
        if obj.reimbursement_status != "pending_reimbursement":
            raise ValueError("只能报销待报销状态的记录")

        before = self._expense_to_dict(obj)
        obj = await self.repo.update_expense(obj, {
            "reimbursement_status": "reimbursed",
            "reimbursed_at": datetime.now(),
            "reimbursed_by": self._user_id(),
        })
        await self._log(obj.ledger_id, ACTION_REIMBURSE, "expense", obj.id, before=before, after=self._expense_to_dict(obj), remark=remark)
        return self._expense_to_dict(obj)

    def _expense_to_dict(self, e):
        return {
            "id": str(e.id),
            "ledger_id": str(e.ledger_id),
            "expense_date": e.expense_date.strftime("%Y-%m-%d") if e.expense_date else None,
            "personnel_id": str(e.personnel_id),
            "name": e.personnel.name if e.personnel else None,
            "expense_type": e.expense_type,
            "amount": float(e.amount),
            "payment_method": e.payment_method,
            "paid_by_personnel": e.paid_by_personnel,
            "receipt_url": e.receipt_url,
            "description": e.description,
            "review_status": e.review_status,
            "reimbursement_status": e.reimbursement_status,
            "reimbursed_at": e.reimbursed_at.isoformat() if e.reimbursed_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }

    async def _sum_expenses_for_ledger(self, ledger_id) -> float:
        """汇总台账下所有已审核通过的费用金额"""
        from sqlalchemy import select, func
        from app.models.aerial import AerialPersonnelExpense
        q = select(func.coalesce(func.sum(AerialPersonnelExpense.amount), 0)).where(
            AerialPersonnelExpense.ledger_id == ledger_id,
            AerialPersonnelExpense.review_status == "approved",
        )
        result = (await self.db.execute(q)).scalar()
        return float(result)

    async def _sum_wages_for_ledger(self, ledger_id) -> float:
        """汇总台账下所有工资金额"""
        from sqlalchemy import select, func
        from app.models.aerial import AerialPersonnelWage
        q = select(func.coalesce(func.sum(AerialPersonnelWage.final_wage_amount), 0)).where(
            AerialPersonnelWage.ledger_id == ledger_id,
        )
        result = (await self.db.execute(q)).scalar()
        return float(result)

    # ── 人员工资 ──────────────────────────────────────────────────────────

    async def list_wages(self, page=1, page_size=20, **filters):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_wages(skip=skip, limit=page_size, **filters)
        return [self._wage_to_dict(w) for w in items], total

    async def create_wage(self, data: dict):
        if not data.get("personnel_id"):
            raise ValueError("人员不能为空")
        data["personnel_id"] = uuid.UUID(data["personnel_id"])
        if data.get("ledger_id"):
            data["ledger_id"] = uuid.UUID(data["ledger_id"])

        # 计算最终工资
        final = float(data.get("final_wage_amount", 0) or 0)
        if final == 0:
            base = float(data.get("base_wage", 0) or 0)
            trip = float(data.get("trip_wage", 0) or 0)
            hourly = float(data.get("hourly_wage", 0) or 0)
            commission = float(data.get("commission_amount", 0) or 0)
            allowance = float(data.get("allowance_amount", 0) or 0)
            deduction = float(data.get("deduction_amount", 0) or 0)
            final = base + trip + hourly + commission + allowance - deduction
            data["final_wage_amount"] = max(0, final)

        obj = await self.repo.create_wage(data)

        # 更新台账工资金额（重新汇总所有工资，避免重复累加）
        if obj.ledger_id:
            ledger = await self.repo.get_ledger(obj.ledger_id)
            if ledger:
                total_wages = await self._sum_wages_for_ledger(obj.ledger_id)
                await self.repo.update_ledger(ledger, {"personnel_wage_amount": total_wages})

        return self._wage_to_dict(obj)

    async def pay_wage(self, wage_id: str, remark: str = ""):
        obj = await self.repo.get_wage(uuid.UUID(wage_id))
        if not obj:
            raise ValueError("工资记录不存在")
        before = self._wage_to_dict(obj)
        obj = await self.repo.update_wage(obj, {
            "payment_status": "paid",
            "paid_at": datetime.now(),
            "paid_by": self._user_id(),
        })
        if obj.ledger_id:
            await self._log(obj.ledger_id, ACTION_PAY_WAGE, "wage", obj.id, before=before, after=self._wage_to_dict(obj), remark=remark)
        return self._wage_to_dict(obj)

    def _wage_to_dict(self, w):
        return {
            "id": str(w.id),
            "ledger_id": str(w.ledger_id) if w.ledger_id else None,
            "wage_month": w.wage_month,
            "personnel_id": str(w.personnel_id),
            "name": w.personnel.name if w.personnel else None,
            "wage_type": w.wage_type,
            "base_wage": float(w.base_wage),
            "trip_wage": float(w.trip_wage),
            "hourly_wage": float(w.hourly_wage),
            "commission_amount": float(w.commission_amount),
            "allowance_amount": float(w.allowance_amount),
            "deduction_amount": float(w.deduction_amount),
            "final_wage_amount": float(w.final_wage_amount),
            "payment_status": w.payment_status,
            "paid_at": w.paid_at.isoformat() if w.paid_at else None,
            "remark": w.remark,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }

    # ── 车辆费用 ────────────────────────────────────────────────────────────

    async def list_costs(self, page=1, page_size=20, **filters):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_costs(skip=skip, limit=page_size, **filters)
        return [self._cost_to_dict(c) for c in items], total

    async def create_cost(self, data: dict):
        if float(data.get("amount", 0)) <= 0:
            raise ValueError("金额必须大于 0")
        data["aerial_vehicle_id"] = uuid.UUID(data["aerial_vehicle_id"])
        if data.get("ledger_id"):
            data["ledger_id"] = uuid.UUID(data["ledger_id"])
        data["cost_date"] = datetime.fromisoformat(data["cost_date"]) if isinstance(data.get("cost_date"), str) else data.get("cost_date", datetime.now())
        for k in ["handler_id", "payer_id"]:
            if data.get(k):
                data[k] = uuid.UUID(data[k])

        obj = await self.repo.create_cost(data)

        # 如果关联台账，更新台账车辆费用
        if obj.ledger_id:
            ledger = await self.repo.get_ledger(obj.ledger_id)
            if ledger:
                new_cost = float(ledger.vehicle_direct_cost) + float(obj.amount)
                await self.repo.update_ledger(ledger, {"vehicle_direct_cost": new_cost})

        return self._cost_to_dict(obj)

    async def review_cost(self, cost_id: str, status: str, remark: str = ""):
        obj = await self.repo.get_cost(uuid.UUID(cost_id))
        if not obj:
            raise ValueError("费用记录不存在")
        if obj.review_status != "pending":
            raise ValueError("只能审核待审核状态的记录")

        before = self._cost_to_dict(obj)
        obj = await self.repo.update_cost(obj, {
            "review_status": status,
            "reviewed_by": self._user_id(),
            "reviewed_at": datetime.now(),
        })
        after = self._cost_to_dict(obj)
        await self._log(
            obj.ledger_id, ACTION_REVIEW, "vehicle_cost", obj.id,
            before=before, after=after, remark=remark
        )
        return after

    def _cost_to_dict(self, c):
        return {
            "id": str(c.id),
            "aerial_vehicle_id": str(c.aerial_vehicle_id),
            "plate_number": c.aerial_vehicle.plate_number if c.aerial_vehicle else None,
            "ledger_id": str(c.ledger_id) if c.ledger_id else None,
            "cost_date": c.cost_date.strftime("%Y-%m-%d") if c.cost_date else None,
            "cost_type": c.cost_type,
            "amount": float(c.amount),
            "handler_id": str(c.handler_id) if c.handler_id else None,
            "payer_id": str(c.payer_id) if c.payer_id else None,
            "payer_name": c.payer.name if c.payer else None,
            "payment_method": c.payment_method,
            "is_personnel_advance": c.is_personnel_advance,
            "need_reimbursement": c.need_reimbursement,
            "receipt_url": c.receipt_url,
            "allocation_type": c.allocation_type,
            "allocation_month": c.allocation_month,
            "review_status": c.review_status,
            "remark": c.remark,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    # ── 安全检查 ────────────────────────────────────────────────────────────

    async def list_safety_checks(self, ledger_id: str, check_type: str = None):
        items = await self.repo.list_safety_checks(ledger_id, check_type)
        return [self._safety_check_to_dict(s) for s in items]

    async def create_safety_check(self, data: dict):
        data["ledger_id"] = uuid.UUID(data["ledger_id"])
        if data.get("checker_id"):
            data["checker_id"] = uuid.UUID(data["checker_id"])

        # 判断检查结果
        checks = [
            "vehicle_appearance_ok", "tire_ok", "brake_ok", "light_ok",
            "hydraulic_system_ok", "outriggers_ok", "platform_ok",
            "safety_belt_ok", "warning_equipment_ok", "extinguisher_ok",
            "documents_ok", "weather_ok", "site_risk_ok",
        ]
        all_ok = all(data.get(c, True) for c in checks)
        if not all_ok:
            data["check_result"] = "failed"
            # 更新台账异常标记
            ledger = await self.repo.get_ledger(data["ledger_id"])
            if ledger:
                await self.repo.update_ledger(ledger, {
                    "abnormal_flag": True,
                    "abnormal_description": data.get("issue_description", "安全检查未通过"),
                })

        obj = await self.repo.create_safety_check(data)
        return self._safety_check_to_dict(obj)

    def _safety_check_to_dict(self, s):
        return {
            "id": str(s.id),
            "ledger_id": str(s.ledger_id),
            "check_type": s.check_type,
            "checker_id": str(s.checker_id) if s.checker_id else None,
            "vehicle_appearance_ok": s.vehicle_appearance_ok,
            "tire_ok": s.tire_ok,
            "brake_ok": s.brake_ok,
            "light_ok": s.light_ok,
            "hydraulic_system_ok": s.hydraulic_system_ok,
            "outriggers_ok": s.outriggers_ok,
            "platform_ok": s.platform_ok,
            "safety_belt_ok": s.safety_belt_ok,
            "warning_equipment_ok": s.warning_equipment_ok,
            "extinguisher_ok": s.extinguisher_ok,
            "documents_ok": s.documents_ok,
            "weather_ok": s.weather_ok,
            "site_risk_ok": s.site_risk_ok,
            "issue_description": s.issue_description,
            "photo_urls": s.photo_urls,
            "check_result": s.check_result,
            "checked_at": s.checked_at.isoformat() if s.checked_at else None,
        }

    # ── 附件 ────────────────────────────────────────────────────────────────

    async def list_attachments(self, ledger_id: str, attachment_type: str = None):
        items = await self.repo.list_attachments(ledger_id, attachment_type)
        return [self._attachment_to_dict(a) for a in items]

    async def create_attachment(self, data: dict):
        data["ledger_id"] = uuid.UUID(data["ledger_id"])
        if data.get("uploaded_by"):
            data["uploaded_by"] = uuid.UUID(data["uploaded_by"])
        else:
            data["uploaded_by"] = self._user_id()
        obj = await self.repo.create_attachment(data)
        return self._attachment_to_dict(obj)

    async def delete_attachment(self, attachment_id: str):
        obj = await self.repo.delete_attachment(uuid.UUID(attachment_id))
        if not obj:
            raise ValueError("附件不存在")
        return {"id": attachment_id, "deleted": True}

    def _attachment_to_dict(self, a):
        return {
            "id": str(a.id),
            "ledger_id": str(a.ledger_id),
            "attachment_type": a.attachment_type,
            "file_url": a.file_url,
            "file_name": a.file_name,
            "uploaded_by": str(a.uploaded_by) if a.uploaded_by else None,
            "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
            "remark": a.remark,
        }

    # ── 审计日志 ────────────────────────────────────────────────────────────

    async def list_audit_logs(self, ledger_id: str = None, page=1, page_size=50):
        skip = (page - 1) * page_size
        items, total = await self.repo.list_audit_logs(ledger_id, skip, page_size)
        return [self._audit_log_to_dict(a) for a in items], total

    def _audit_log_to_dict(self, a):
        return {
            "id": str(a.id),
            "ledger_id": str(a.ledger_id) if a.ledger_id else None,
            "operator_id": str(a.operator_id) if a.operator_id else None,
            "action": a.action,
            "source": a.source,
            "target_type": a.target_type,
            "target_id": str(a.target_id) if a.target_id else None,
            "before_json": a.before_json,
            "after_json": a.after_json,
            "remark": a.remark,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    # ── 首页 Dashboard ─────────────────────────────────────────────────────

    async def get_dashboard_overview(self):
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        year_month = today.strftime("%Y-%m")

        daily = await self.repo.get_daily_summary(today_str)
        monthly = await self.repo.get_monthly_summary(year_month)

        return {
            "today": daily,
            "monthly": monthly,
        }

    async def get_today_ledgers(self):
        today_str = date.today().strftime("%Y-%m-%d")
        items, _ = await self.repo.list_ledgers(date_from=today_str, date_to=today_str, limit=100)
        return [self._ledger_to_dict(l) for l in items]

    async def get_reminders(self):
        from datetime import timedelta
        now = datetime.now()
        soon = now + timedelta(days=30)

        vehicles, _ = await self.repo.list_vehicles(limit=100)
        reminders = []
        for v in vehicles:
            if v.insurance_expire_date and v.insurance_expire_date <= soon:
                days = (v.insurance_expire_date - now).days
                reminders.append({"type": "insurance", "vehicle": v.vehicle_name, "plate": v.plate_number, "expire_date": v.insurance_expire_date.strftime("%Y-%m-%d"), "days_left": days, "urgent": days <= 7})
            if v.inspection_expire_date and v.inspection_expire_date <= soon:
                days = (v.inspection_expire_date - now).days
                reminders.append({"type": "inspection", "vehicle": v.vehicle_name, "plate": v.plate_number, "expire_date": v.inspection_expire_date.strftime("%Y-%m-%d"), "days_left": days, "urgent": days <= 7})
            if v.maintenance_due_date and v.maintenance_due_date <= soon:
                days = (v.maintenance_due_date - now).days
                reminders.append({"type": "maintenance", "vehicle": v.vehicle_name, "plate": v.plate_number, "due_date": v.maintenance_due_date.strftime("%Y-%m-%d"), "days_left": days, "urgent": days <= 7})
        return sorted(reminders, key=lambda r: r["days_left"])

    # ── 报表 ────────────────────────────────────────────────────────────────

    async def get_report_daily(self, date_str: str):
        summary = await self.repo.get_daily_summary(date_str)
        items, _ = await self.repo.list_ledgers(date_from=date_str, date_to=date_str, limit=100)
        summary["ledgers"] = [self._ledger_to_dict(l) for l in items]
        return summary

    async def get_report_monthly(self, year_month: str):
        summary = await self.repo.get_monthly_summary(year_month)
        avg_trip_revenue = summary["receivable"] / summary["trip_count"] if summary["trip_count"] else 0
        avg_trip_cost = (summary["wages"] + summary["reimbursements"] + summary["vehicle_costs"]) / summary["trip_count"] if summary["trip_count"] else 0
        avg_trip_profit = summary["gross_profit"] / summary["trip_count"] if summary["trip_count"] else 0
        summary["avg_trip_revenue"] = round(avg_trip_revenue, 2)
        summary["avg_trip_cost"] = round(avg_trip_cost, 2)
        summary["avg_trip_profit"] = round(avg_trip_profit, 2)
        return summary

    async def get_report_receivables(self, page=1, page_size=20):
        items, total = await self.repo.get_unpaid_ledgers((page - 1) * page_size, page_size)
        ledgers = [self._ledger_to_dict(l) for l in items]
        total_unpaid = sum(l["unpaid_amount"] for l in ledgers)
        return {"items": ledgers, "total": total, "total_unpaid": total_unpaid}

    async def get_report_reimbursements(self, page=1, page_size=20):
        pending_expenses, pe_total = await self.repo.get_pending_expenses()
        pending_reimb, pr_total = await self.repo.get_pending_reimbursements((page - 1) * page_size, page_size)
        return {
            "pending_review": [self._expense_to_dict(e) for e in pending_expenses],
            "pending_review_total": pe_total,
            "pending_reimbursement": [self._expense_to_dict(e) for e in pending_reimb],
            "pending_reimbursement_total": pr_total,
        }

    async def get_report_costs(self, year_month: str = None):
        return await self.repo.get_cost_by_type(year_month)

    async def get_report_personnel_summary(self, year_month: str):
        return await self.repo.get_personnel_summary(year_month)
