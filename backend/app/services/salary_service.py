import logging
import re
from uuid import UUID
from datetime import date, datetime, timedelta
from calendar import monthrange
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.repositories.salary_repo import SalaryRecordRepository
from app.models.employee import Employee
from app.models.salary_rule import SalaryRule
from app.models.attendance import AttendanceRecord
from app.models.salary_grid import SalaryItem, SalaryGridValue, SalaryParam, SalaryParamValue
from app.services.salary_formula import (
    FUNCTIONS,
    RAW_VARS,
    FormulaError,
    build_dependency_order,
    evaluate_formula,
    validate_formula,
)

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

        # 全勤/话费补助优先取工资网格算出的值（无则回退工资规则标准）
        att_grid = await self._grid_values(month, ["att_bonus"])

        rows = []
        for r in records:
            eid = r.employee_id
            emp = await self._load_employee(eid)
            rule = await self._latest_rule(eid, end)
            att = att_map.get(str(eid), {"normal": 0, "half": 0, "missed": 0, "absent": 0,
                                         "records": 0, "overtime": 0})

            base = float(r.base_salary or 0)
            overtime_pay = float(r.overtime_pay or 0)
            # 绩效/伙食优先取工资记录值（工资网格生成/手改时已同步），无则回退规则标准
            performance = (float(r.bonus) if r.bonus is not None
                           else (float(rule.bonus_standard) if rule and rule.bonus_standard else 0.0))
            meal = (float(r.subsidy) if r.subsidy is not None
                    else (float(rule.subsidy_standard) if rule and rule.subsidy_standard else 0.0))
            attendance_bonus = att_grid.get((str(eid), "att_bonus"))
            if attendance_bonus is None:
                attendance_bonus = (float(rule.attendance_bonus) if rule and rule.attendance_bonus else 0.0)
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

    # ── 工资网格（考勤式）：指标列 + 可编辑公式 + 单元格值 ─────────────────

    @staticmethod
    def _check_month(month):
        if len(month) != 7 or month[4] != "-" or not month[:4].isdigit() or not month[5:].isdigit():
            raise ValueError("月份格式应为 YYYY-MM")

    async def list_items(self):
        """全部指标（含停用），按 sort_order 排序。"""
        r = await self.db.execute(
            select(SalaryItem).order_by(SalaryItem.sort_order, SalaryItem.created_at)
        )
        return [self._item_d(i) for i in r.scalars().all()]

    def _item_d(self, i):
        return {
            "id": str(i.id),
            "key": i.key,
            "label": i.label,
            "formula": i.formula,
            "sort_order": i.sort_order,
            "is_active": bool(i.is_active),
            "is_builtin": bool(i.is_builtin),
            "is_manual": bool(i.is_manual),
        }

    async def _all_item_keys(self, exclude=None):
        r = await self.db.execute(select(SalaryItem))
        return [i.key for i in r.scalars().all() if i.key != exclude]

    async def _all_param_keys(self):
        """全部参数 key（公式可引用的变量名）。"""
        r = await self.db.execute(select(SalaryParam))
        return [p.key for p in r.scalars().all()]

    async def create_item(self, data):
        key = (data.get("key") or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError("指标 key 只能包含字母、数字、下划线，且不能以数字开头")
        if key in RAW_VARS:
            raise ValueError(f"指标 key「{key}」与系统内置变量同名，请换一个")
        if key in FUNCTIONS:
            raise ValueError(f"指标 key「{key}」是函数名，请换一个")
        existing_keys = await self._all_item_keys()
        if key in existing_keys:
            raise ValueError(f"指标 key「{key}」已存在")
        is_manual = bool(data.get("is_manual"))
        formula = ""
        if not is_manual:
            # 公式可引用其他指标 key + 参数 key；手工填写列无需公式
            formula = (data.get("formula") or "0").strip()
            param_keys = await self._all_param_keys()
            validate_formula(formula, existing_keys, param_keys)
        item = SalaryItem(
            key=key,
            label=(data.get("label") or key).strip(),
            formula=formula,
            sort_order=int(data.get("sort_order") or 0),
            is_active=True,
            is_builtin=False,
            is_manual=is_manual,
        )
        self.db.add(item)
        await self.db.flush()
        return self._item_d(item)

    async def update_item(self, item_id: UUID, data):
        r = await self.db.execute(select(SalaryItem).where(SalaryItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise ValueError("指标不存在")
        if "is_manual" in data and data["is_manual"] is not None:
            item.is_manual = bool(data["is_manual"])
            if item.is_manual:
                item.formula = ""
        if "formula" in data and data["formula"] is not None and not item.is_manual:
            other_keys = [k for k in await self._all_item_keys() if k != item.key]
            param_keys = await self._all_param_keys()
            validate_formula(data["formula"], other_keys, param_keys)
            item.formula = data["formula"]
        if data.get("label") is not None:
            item.label = data["label"]
        if "sort_order" in data and data["sort_order"] is not None:
            item.sort_order = int(data["sort_order"])
        if "is_active" in data and data["is_active"] is not None:
            item.is_active = bool(data["is_active"])
        await self.db.flush()
        return self._item_d(item)

    async def delete_item(self, item_id: UUID):
        r = await self.db.execute(select(SalaryItem).where(SalaryItem.id == item_id))
        item = r.scalar_one_or_none()
        if not item:
            raise ValueError("指标不存在")
        if item.is_builtin:
            raise ValueError("内置指标不可删除，可在设置中停用")
        await self.db.execute(delete(SalaryGridValue).where(SalaryGridValue.item_key == item.key))
        await self.db.delete(item)
        await self.db.flush()
        return True

    def _rule_vars(self, rule):
        """工资规则数值 → 公式原始变量（无规则/缺省一律 0）。"""
        def f(v):
            return float(v) if v is not None else 0.0
        if not rule:
            return {k: 0.0 for k in
                    ("base", "ot_rate", "bonus_std", "commission_rate", "subsidy_std",
                     "att_bonus", "social", "housing", "ded_std")}
        return {
            "base": f(rule.base_salary),
            "ot_rate": f(rule.overtime_rate),
            "bonus_std": f(rule.bonus_standard),
            "commission_rate": f(rule.commission_rate),
            "subsidy_std": f(rule.subsidy_standard),
            "att_bonus": f(rule.attendance_bonus),
            "social": f(rule.social_insurance),
            "housing": f(rule.housing_fund),
            "ded_std": f(rule.deduction_standard),
        }

    def _attendance_vars(self, att, work_days):
        """考勤统计 → 公式原始变量。att 结构同 _attendance_stats 返回。"""
        normal = float(att.get("normal") or 0)
        half = float(att.get("half") or 0)
        records = float(att.get("records") or 0)
        return {
            "ot_hours": float(att.get("overtime") or 0),
            "attend_days": normal + half * 0.5,
            "half_days": half,
            "missed_days": float(att.get("missed") or 0),
            "absent_days": float(max(0, work_days - records)) + float(att.get("absent") or 0),
            "records": records,
            "work_days": float(work_days),
        }

    async def _grid_values(self, month, item_keys=None, with_source=False):
        """某月网格值 {(employee_id_str, item_key): float|None}。

        with_source=True 时值为 (float|None, source)，用于区分手工/计算来源。
        """
        stmt = select(SalaryGridValue).where(SalaryGridValue.month == month)
        if item_keys:
            stmt = stmt.where(SalaryGridValue.item_key.in_(item_keys))
        r = await self.db.execute(stmt)
        out = {}
        for v in r.scalars().all():
            val = float(v.value) if v.value is not None else None
            out[(str(v.employee_id), v.item_key)] = (val, v.source) if with_source else val
        return out

    async def _upsert_grid_value(self, month, eid: UUID, key, value, source):
        r = await self.db.execute(
            select(SalaryGridValue).where(
                SalaryGridValue.month == month,
                SalaryGridValue.employee_id == eid,
                SalaryGridValue.item_key == key,
            )
        )
        gv = r.scalar_one_or_none()
        if gv:
            gv.value = value
            gv.source = source
        else:
            self.db.add(SalaryGridValue(month=month, employee_id=eid, item_key=key,
                                        value=value, source=source))
        await self.db.flush()

    async def _replace_grid_values(self, month, eid: UUID, vals, manual_keys=()):
        """覆盖某员工某月全部网格值（生成用）。

        manual_keys 中的单元格以 source=manual 落库，保留手工标记，
        这样下次生成时这些格子不会被重新计算覆盖。
        """
        await self.db.execute(
            delete(SalaryGridValue).where(
                SalaryGridValue.month == month, SalaryGridValue.employee_id == eid
            )
        )
        for key, value in vals.items():
            source = "manual" if key in manual_keys else "computed"
            self.db.add(SalaryGridValue(month=month, employee_id=eid, item_key=key,
                                        value=value, source=source))
        await self.db.flush()

    # 指标 key → salary_records 映射列（生成/手改后同步，让旧报表与发放逻辑继续工作）
    RECORD_MAP = {
        "basic": "base_salary",
        "overtime_pay": "overtime_pay",
        "bonus": "bonus",
        "subsidy": "subsidy",
        "deduction": "deduction",
        "net": "net_salary",
    }

    async def _upsert_record(self, month, eid: UUID, vals):
        """把网格计算结果同步进 salary_records（有则更新，无则创建 pending）。"""
        data = {
            "base_salary": float(vals.get("basic") or 0),
            "overtime_pay": float(vals.get("overtime_pay") or 0),
            "bonus": float(vals.get("bonus") or 0),
            "subsidy": float(vals.get("subsidy") or 0),
            "deduction": float(vals.get("deduction") or 0),
            "net_salary": float(vals.get("net") or 0),
        }
        existing = await self._existing_record(eid, month)
        if existing:
            await self.repo.update(existing, data)
        else:
            data.update({
                "employee_id": eid,
                "month": month,
                "payment_status": "pending",
                "commission": 0,
                "remark": None,
            })
            await self.repo.create(data)

    # ── 工资参数（每月手工填一个值，公式可引用）──────────────────────────────

    async def _param_values_for_month(self, month) -> dict:
        """当月参数取值 {key: float}；未填值的参数补 0。"""
        params = (await self.db.execute(select(SalaryParam))).scalars().all()
        if not params:
            return {}
        pid_map = {p.id: p.key for p in params}
        r = await self.db.execute(select(SalaryParamValue).where(SalaryParamValue.month == month))
        vals = {}
        for v in r.scalars().all():
            key = pid_map.get(v.param_id)
            if key:
                vals[key] = float(v.value) if v.value is not None else 0.0
        for p in params:
            vals.setdefault(p.key, 0.0)
        return vals

    async def list_params(self, month):
        """参数定义 + 当月取值（未填为 null）。"""
        self._check_month(month)
        params = (await self.db.execute(
            select(SalaryParam).order_by(SalaryParam.sort_order, SalaryParam.created_at)
        )).scalars().all()
        r = await self.db.execute(select(SalaryParamValue).where(SalaryParamValue.month == month))
        value_map = {v.param_id: v for v in r.scalars().all()}
        out = []
        for p in params:
            v = value_map.get(p.id)
            out.append({
                "id": str(p.id),
                "key": p.key,
                "label": p.label,
                "sort_order": p.sort_order,
                "value": float(v.value) if v and v.value is not None else None,
            })
        return {"month": month, "params": out}

    async def create_param(self, data):
        key = (data.get("key") or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError("参数 key 只能包含字母、数字、下划线，且不能以数字开头")
        if key in RAW_VARS:
            raise ValueError(f"参数 key「{key}」与系统内置变量同名，请换一个")
        if key in FUNCTIONS:
            raise ValueError(f"参数 key「{key}」是函数名，请换一个")
        if key in await self._all_item_keys():
            raise ValueError(f"参数 key「{key}」与工资指标同名，请换一个")
        if key in await self._all_param_keys():
            raise ValueError(f"参数 key「{key}」已存在")
        p = SalaryParam(key=key, label=(data.get("label") or key).strip(),
                        sort_order=int(data.get("sort_order") or 0))
        self.db.add(p)
        await self.db.flush()
        return {"id": str(p.id), "key": p.key, "label": p.label, "sort_order": p.sort_order}

    async def update_param(self, param_id: UUID, data):
        r = await self.db.execute(select(SalaryParam).where(SalaryParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise ValueError("参数不存在")
        if data.get("label") is not None:
            p.label = data["label"]
        if "sort_order" in data and data["sort_order"] is not None:
            p.sort_order = int(data["sort_order"])
        await self.db.flush()
        return {"id": str(p.id), "key": p.key, "label": p.label, "sort_order": p.sort_order}

    async def delete_param(self, param_id: UUID):
        r = await self.db.execute(select(SalaryParam).where(SalaryParam.id == param_id))
        p = r.scalar_one_or_none()
        if not p:
            raise ValueError("参数不存在")
        await self.db.execute(delete(SalaryParamValue).where(SalaryParamValue.param_id == param_id))
        await self.db.delete(p)
        await self.db.flush()
        return True

    async def save_param_values(self, month, values):
        """保存某月参数值：values=[{key, value}]，value=None 表示清空该月取值。"""
        self._check_month(month)
        params = {p.key: p.id for p in (await self.db.execute(select(SalaryParam))).scalars().all()}
        saved = 0
        errors = []
        for it in values or []:
            key = it.get("key")
            pid = params.get(key)
            if not pid:
                errors.append(f"未知参数：{key}")
                continue
            value = it.get("value")
            value = float(value) if value not in (None, "") else None
            r = await self.db.execute(select(SalaryParamValue).where(
                SalaryParamValue.month == month, SalaryParamValue.param_id == pid))
            row = r.scalar_one_or_none()
            if value is None:
                if row:
                    await self.db.delete(row)
                continue
            if row:
                row.value = value
            else:
                self.db.add(SalaryParamValue(month=month, param_id=pid, value=value))
            saved += 1
        await self.db.flush()
        return {"month": month, "saved": saved, "errors": errors}

    async def compute_month(self, month, employee_ids: list[UUID] | None = None):
        """按指标公式计算当月所有（或指定）员工的工资网格值并落库。

        结果写 salary_grid_values(source=computed，覆盖该月全部单元格)，
        并同步 salary_records（映射列）。返回 {month, computed, errors}。
        """
        self._check_month(month)
        year, mon = int(month[:4]), int(month[5:])
        start = date(year, mon, 1)
        end = date(year, mon, monthrange(year, mon)[1])
        work_days = sum(1 for d in range(1, end.day + 1) if date(year, mon, d).weekday() < 5)

        items = await self.list_items()
        active = [i for i in items if i["is_active"]]
        if not active:
            raise ValueError("请先在「指标设置」中启用至少一个指标")
        manual_keys = {i["key"] for i in active if i.get("is_manual")}
        computed_items = [i for i in active if not i.get("is_manual")]
        if not computed_items:
            raise ValueError("没有公式指标可计算（请把至少一个指标改为公式计算）")
        formula_map = {i["key"]: i["formula"] for i in computed_items}
        active_keys = set(formula_map)
        params = await self._param_values_for_month(month)
        extra = manual_keys | set(params)
        order = build_dependency_order(formula_map, extra)  # 循环引用→FormulaError(ValueError)

        targets = employee_ids or [e.id for e in await self._active_employees()]
        att_map = await self._attendance_stats(start, end)
        existing = await self._grid_values(month, with_source=True)  # {(eid,key):(value,source)}

        computed = 0
        errors = []
        for eid in targets:
            rule = await self._latest_rule(eid, end)
            att = att_map.get(str(eid), {"normal": 0, "half": 0, "missed": 0, "absent": 0,
                                         "records": 0, "overtime": 0})
            raw = self._rule_vars(rule)
            raw.update(self._attendance_vars(att, work_days))
            raw.update(params)

            # 手工钉住：手工填写列 + 手工改过的单元格，不再参与重新计算
            preserve = {}
            for key in active_keys | manual_keys:
                cell = existing.get((str(eid), key))
                if cell and cell[0] is not None and (cell[1] == "manual" or key in manual_keys):
                    preserve[key] = cell[0]
            for k in manual_keys:
                raw[k] = preserve.get(k, 0.0)

            vals = dict(preserve)
            try:
                for key in order:
                    if key in preserve:
                        continue  # 手工钉住，跳过重算
                    vals[key] = round(
                        evaluate_formula(formula_map[key], {**raw, **vals}, active_keys), 2
                    )
                await self._replace_grid_values(month, eid, vals, set(preserve))
                await self._upsert_record(month, eid, vals)
                computed += 1
            except FormulaError as e:
                errors.append(f"{await self._emp_name(eid)}: {e}")
        return {"month": month, "computed": computed, "errors": errors}

    async def _emp_name(self, eid: UUID):
        emp = await self._load_employee(eid)
        return emp.name if emp else str(eid)

    async def get_grid(self, month):
        """考勤式工资网格数据：指标列 + 全部在职员工行 + 网格值 + 支付状态。"""
        self._check_month(month)
        items = [i for i in await self.list_items() if i["is_active"]]
        employees = await self._active_employees()
        gv_map = await self._grid_values(month)
        records, _ = await self.repo.list(0, 10000, month=month)
        status_map = {str(r.employee_id): r for r in records}
        rows = []
        for e in employees:
            eid = str(e.id)
            rec = status_map.get(eid)
            rows.append({
                "employee_id": eid,
                "employee_no": e.employee_no,
                "employee_name": e.name,
                "department": e.department,
                "values": {it["key"]: gv_map.get((eid, it["key"])) for it in items},
                "payment_status": rec.payment_status if rec else None,
                "paid_at": rec.paid_at.isoformat() if rec and rec.paid_at else None,
            })
        return {"month": month, "items": items, "rows": rows}

    async def save_cells(self, month, cells=None, payments=None):
        """保存网格手工修改的单元格与支付状态。

        cells: [{employee_id, item_key, value}]；payments: [{employee_id, payment_status}]。
        单元格写 salary_grid_values(source=manual)，映射列同步 salary_records。
        """
        self._check_month(month)
        items = await self.list_items()
        valid_keys = {i["key"] for i in items}
        errors = []
        saved = 0
        touched = set()
        for c in cells or []:
            key = c.get("item_key")
            if key not in valid_keys:
                errors.append(f"未知指标：{key}")
                continue
            eid = UUID(c["employee_id"])
            value = c.get("value")
            value = float(value) if value not in (None, "") else None
            await self._upsert_grid_value(month, eid, key, value, "manual")
            saved += 1
            touched.add(str(eid))
        if touched:
            gv_map = await self._grid_values(month)
            for eid_str in touched:
                data = {}
                for key, col in self.RECORD_MAP.items():
                    v = gv_map.get((eid_str, key))
                    if v is not None:
                        data[col] = v
                if not data:
                    continue
                existing = await self._existing_record(UUID(eid_str), month)
                if existing:
                    await self.repo.update(existing, data)
                else:
                    data.update({
                        "employee_id": UUID(eid_str), "month": month,
                        "base_salary": data.get("base_salary", 0),
                        "net_salary": data.get("net_salary", 0),
                        "payment_status": "pending", "commission": 0,
                    })
                    await self.repo.create(data)
        for p in payments or []:
            eid = UUID(p["employee_id"])
            status = p.get("payment_status")
            existing = await self._existing_record(eid, month)
            if existing:
                upd = {"payment_status": status}
                if status == "paid":
                    upd["paid_at"] = existing.paid_at or datetime.utcnow()
                else:
                    upd["paid_at"] = None
                await self.repo.update(existing, upd)
            else:
                await self.repo.create({
                    "employee_id": eid, "month": month,
                    "base_salary": 0, "net_salary": 0,
                    "payment_status": status, "commission": 0,
                })
        return {"month": month, "saved": saved, "errors": errors}

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
