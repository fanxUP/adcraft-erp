import logging
from uuid import UUID
from datetime import date, timedelta
from calendar import monthrange
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.salary_repo import SalaryRecordRepository
from app.models.employee import Employee
from app.models.salary_rule import SalaryRule
from app.models.attendance import AttendanceRecord

logger = logging.getLogger(__name__)

# 月计薪天数 / 每日小时数，用于把月基本工资换算成时薪
MONTHLY_WORK_DAYS = 21.75
DAILY_WORK_HOURS = 8


class SalaryRecordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SalaryRecordRepository(db)

    async def _load_employee(self, eid: UUID):
        r = await self.db.execute(select(Employee).where(Employee.id == eid, Employee.deleted_at.is_(None)))
        return r.scalar_one_or_none()

    async def list_records(self, page=1, page_size=20, employee_id=None, month=None, payment_status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list(skip, page_size, employee_id, month, payment_status)
        result = []
        for r in records:
            d = self._d(r)
            emp = await self._load_employee(r.employee_id)
            if emp:
                d["employee_no"] = emp.employee_no
                d["employee_name"] = emp.name
            result.append(d)
        return result, total

    async def get_record(self, sid: UUID):
        r = await self.repo.get_by_id(sid)
        if not r:
            return None
        d = self._d(r)
        emp = await self._load_employee(r.employee_id)
        if emp:
            d["employee_no"] = emp.employee_no
            d["employee_name"] = emp.name
        return d

    async def create_record(self, data):
        if isinstance(data.get("employee_id"), str):
            data["employee_id"] = UUID(data["employee_id"])
        return self._d(await self.repo.create(data))

    async def update_record(self, sid: UUID, data):
        r = await self.repo.get_by_id(sid)
        if not r:
            raise ValueError("工资记录不存在")
        return self._d(await self.repo.update(r, data))

    async def delete_record(self, sid: UUID):
        r = await self.repo.get_by_id(sid)
        if not r:
            return False
        await self.repo.delete(r)
        return True

    async def batch_create(self, month: str, employee_ids: list[UUID], base_salary_map: dict):
        """批量生成指定月份的工资记录"""
        created = []
        for eid in employee_ids:
            bs = base_salary_map.get(str(eid), 0)
            data = {
                "employee_id": eid,
                "month": month,
                "base_salary": bs,
                "net_salary": bs,
                "payment_status": "pending",
            }
            created.append(self._d(await self.repo.create(data)))
        return created

    # ── 按工资规则自动生成工资表 ────────────────────────────────────────────

    async def _active_employees(self):
        """在职员工（离职/停职不参与生成）。"""
        r = await self.db.execute(
            select(Employee).where(Employee.employment_status == "active", Employee.deleted_at.is_(None))
        )
        return r.scalars().all()

    async def _latest_rule(self, employee_id: UUID, cutoff: date):
        """员工在 cutoff 之前生效的最新工资规则。"""
        r = await self.db.execute(
            select(SalaryRule)
            .where(SalaryRule.employee_id == employee_id, SalaryRule.effective_date <= cutoff)
            .order_by(SalaryRule.effective_date.desc())
        )
        return r.scalars().first()

    async def _existing_record(self, employee_id: UUID, month: str):
        return await self.repo.get_by_employee_month(employee_id, month)

    async def _monthly_overtime_hours(self, employee_id: UUID, start: date, end: date) -> float:
        r = await self.db.execute(
            select(func.coalesce(func.sum(AttendanceRecord.overtime_hours), 0))
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date >= start,
                AttendanceRecord.date <= end,
            )
        )
        return float(r.scalar() or 0)

    async def _attendance_stats(self, start: date, end: date) -> dict:
        """统计月内每个员工的考勤：出勤/半天/旷工/未出勤记录数、总记录数、加班小时。"""
        r = await self.db.execute(
            select(
                AttendanceRecord.employee_id,
                func.count().filter(AttendanceRecord.check_in_status == "normal").label("normal"),
                func.count().filter(AttendanceRecord.check_in_status == "half_day").label("half"),
                func.count().filter(AttendanceRecord.check_in_status == "missed").label("missed"),
                func.count().filter(AttendanceRecord.check_in_status == "absent").label("absent"),
                func.count().label("records"),
                func.coalesce(func.sum(AttendanceRecord.overtime_hours), 0).label("overtime"),
            )
            .where(AttendanceRecord.date >= start, AttendanceRecord.date <= end)
            .group_by(AttendanceRecord.employee_id)
        )
        result = {}
        for row in r:
            result[str(row.employee_id)] = {
                "normal": int(row.normal or 0),
                "half": int(row.half or 0),
                "missed": int(row.missed or 0),
                "absent": int(row.absent or 0),
                "records": int(row.records or 0),
                "overtime": float(row.overtime or 0),
            }
        return result

    async def generate_month(self, month: str, employee_ids: list[UUID] | None = None) -> dict:
        """按工资规则自动生成指定月份的工资记录。

        口径（生成后可手工微调）：
          base_salary   = 规则.base_salary
          overtime_pay  = 当月考勤加班工时 × 时薪 × 加班费率（时薪 = base / 21.75 / 8）
          bonus         = 规则.bonus_standard（缺省 0）
          commission    = 0（无数据源）
          subsidy       = 规则.subsidy_standard（缺省 0）
          deduction     = 社保 + 公积金 + 其他扣款标准
          net_salary    = base + overtime + bonus + commission + subsidy − deduction（不小于 0）

        无规则的员工跳过；该月已有记录的员工跳过（不覆盖）。
        返回 {month, created, skipped_no_rule, skipped_exists, errors}。
        """
        if len(month) != 7 or month[4] != "-" or not month[:4].isdigit() or not month[5:].isdigit():
            raise ValueError("月份格式应为 YYYY-MM")
        year, mon = int(month[:4]), int(month[5:])
        start = date(year, mon, 1)
        end = date(year, mon, monthrange(year, mon)[1])

        targets = employee_ids if employee_ids else [e.id for e in await self._active_employees()]

        created = 0
        skipped_no_rule = 0
        skipped_exists = 0
        errors = []
        for eid in targets:
            rule = await self._latest_rule(eid, end)
            if rule is None:
                skipped_no_rule += 1
                continue
            if await self._existing_record(eid, month):
                skipped_exists += 1
                continue

            base = float(rule.base_salary or 0)
            overtime_hours = await self._monthly_overtime_hours(eid, start, end)
            rate = float(rule.overtime_rate) if rule.overtime_rate else 1.5
            overtime_pay = round(overtime_hours * (base / MONTHLY_WORK_DAYS / DAILY_WORK_HOURS) * rate, 2)
            bonus = float(rule.bonus_standard or 0)
            subsidy = float(rule.subsidy_standard or 0)
            deduction = (float(rule.social_insurance or 0)
                         + float(rule.housing_fund or 0)
                         + float(rule.deduction_standard or 0))
            net = round(base + overtime_pay + bonus + subsidy - deduction, 2)
            if net < 0:
                net = 0.0

            data = {
                "employee_id": eid,
                "month": month,
                "base_salary": base,
                "overtime_pay": overtime_pay,
                "bonus": bonus,
                "commission": 0,
                "subsidy": subsidy,
                "deduction": deduction,
                "net_salary": net,
                "payment_status": "pending",
            }
            await self.repo.create(data)
            created += 1

        return {
            "month": month,
            "created": created,
            "skipped_no_rule": skipped_no_rule,
            "skipped_exists": skipped_exists,
            "errors": errors,
        }

    # ── 工资报表（仿 Excel「工资计算明细表」）─────────────────────────────────

    async def report_month(self, month: str) -> dict:
        """生成指定月份工资报表，每行 = 一名员工当月一条工资记录。

        列口径：
          出勤天数/旷工/未出勤天数/加班小时 来自当月考勤；
          全勤/绩效/伙食补助/社保/社保扣款 来自月末前生效的最新工资规则；
          基本工资/加班费/备注 来自工资记录；上月 来自上月工资记录。
          应发 = 基本+加班费+绩效+伙食+全勤话费；实发 = 应发 − 社保扣款。
        """
        if len(month) != 7 or month[4] != "-" or not month[:4].isdigit() or not month[5:].isdigit():
            raise ValueError("月份格式应为 YYYY-MM")
        year, mon = int(month[:4]), int(month[5:])
        start = date(year, mon, 1)
        end = date(year, mon, monthrange(year, mon)[1])

        # 上月窗口（用于「上月」列）
        prev = start - timedelta(days=1)
        prev_ym = f"{prev.year}-{prev.month:02d}"

        records, _ = await self.repo.list(0, 10000, month=month)
        prev_records, _ = await self.repo.list(0, 10000, month=prev_ym)
        prev_map = {str(r.employee_id): float(r.net_salary or 0) for r in prev_records}
        att_map = await self._attendance_stats(start, end)

        # 月内非周末天数（未出勤天数 = 无记录的非周末天数 + absent 记录数）
        non_weekend = sum(1 for d in range(1, end.day + 1) if date(year, mon, d).weekday() < 5)

        rows = []
        for r in records:
            eid = r.employee_id
            emp = await self._load_employee(eid)
            rule = await self._latest_rule(eid, end)
            att = att_map.get(str(eid), {"normal": 0, "half": 0, "missed": 0, "absent": 0,
                                         "records": 0, "overtime": 0})

            base = float(r.base_salary or 0)
            overtime_pay = float(r.overtime_pay or 0)
            attendance_bonus = float(rule.attendance_bonus) if rule and rule.attendance_bonus else 0.0
            performance = float(rule.bonus_standard) if rule and rule.bonus_standard else 0.0
            meal = float(rule.subsidy_standard) if rule and rule.subsidy_standard else 0.0
            social = float(rule.social_insurance) if rule and rule.social_insurance else 0.0
            housing = float(rule.housing_fund) if rule and rule.housing_fund else 0.0
            other_ded = float(rule.deduction_standard) if rule and rule.deduction_standard else 0.0

            attend_days = att["normal"] + att["half"] * 0.5
            absent_days = max(0, non_weekend - att["records"]) + att["absent"]
            total_salary = round(base + overtime_pay, 2)
            gross = round(total_salary + performance + meal + attendance_bonus, 2)
            social_deduction = round(social + housing + other_ded, 2)
            net = round(gross - social_deduction, 2)
            if net < 0:
                net = 0.0

            rows.append({
                "employee_no": emp.employee_no if emp else None,
                "department": emp.department if emp else None,
                "employee_name": emp.name if emp else None,
                "attend_days": attend_days,
                "missed_days": att["missed"],
                "attendance_bonus": attendance_bonus,
                "performance": performance,
                "absent_days": absent_days,
                "base_salary": base,
                "overtime_hours": att["overtime"],
                "overtime_pay": overtime_pay,
                "total_salary": total_salary,
                "performance_wage": performance,
                "meal_subsidy": meal,
                "attendance_phone_subsidy": attendance_bonus,
                "gross": gross,
                "social_deduction": social_deduction,
                "net_salary": net,
                "social_insurance": social,
                "actual_gross": net,
                "remark": r.remark,
                "prev_month_net": prev_map.get(str(eid)),
            })

        rows.sort(key=lambda x: (x["department"] or "", x["employee_name"] or ""))
        return {"month": month, "title": f"{year}年{mon}月份工资计算明细表", "rows": rows}

    def _d(self, r):
        return {
            "id": str(r.id),
            "employee_id": str(r.employee_id),
            "month": r.month,
            "base_salary": float(r.base_salary) if r.base_salary else 0,
            "overtime_pay": float(r.overtime_pay) if r.overtime_pay else None,
            "bonus": float(r.bonus) if r.bonus else None,
            "commission": float(r.commission) if r.commission else None,
            "subsidy": float(r.subsidy) if r.subsidy else None,
            "deduction": float(r.deduction) if r.deduction else None,
            "net_salary": float(r.net_salary) if r.net_salary else 0,
            "payment_status": r.payment_status,
            "paid_at": r.paid_at.isoformat() if r.paid_at else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
