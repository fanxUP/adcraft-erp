"""Single attendance interpretation used by the monthly sheet and payroll.

Raw punches and approved leave are kept separately; missing data never becomes
absence. Historical schedules cannot be reconstructed from current rules.
"""
from calendar import monthrange
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime

from sqlalchemy import select, or_
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, AttendanceRule
from app.models.leave import LeaveRequest

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def business_today():
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def month_bounds(month):
    try:
        if len(month) != 7 or month[4] != "-":
            raise ValueError()
        year, mon = map(int, month.split("-"))
        return date(year, mon, 1), date(year, mon, monthrange(year, mon)[1])
    except (ValueError, TypeError):
        raise ValueError("月份格式应为 YYYY-MM") from None


def employed_on(employee, day):
    return (not employee.hire_date or employee.hire_date <= day) and (
        not employee.resignation_date or day <= employee.resignation_date)


def summarize_employee(employee, start, end, records, leaves, work_days=None, today=None):
    today = today or business_today()
    weekdays = set(work_days if work_days is not None else WEEKDAYS[:5])
    summary = dict(normal=0, half=0, missed=0, absent=0, records=0, overtime=0.0,
                   unregistered=0.0, leave=0.0, late=0, work_days=0, conflicts=0)
    by_day = {r.date: r for r in records}
    details = {}
    day = start
    while day <= end:
        key = day.isoformat()
        scheduled = WEEKDAYS[day.weekday()] in weekdays
        applicable = employed_on(employee, day)
        rec = by_day.get(day)
        approved = [l for l in leaves if l.start_date <= day <= l.end_date]
        leave = (0.5 if approved and float(approved[0].duration_days) == 0.5 else 1.0) if approved else 0.0
        detail = dict(status="unregistered", scheduled=scheduled, leave_days=leave)
        if not applicable:
            detail["status"] = "outside_employment"
        elif day > today:
            detail["status"] = "future"
        else:
            if scheduled:
                summary["work_days"] += 1
            if rec:
                summary["records"] += 1
                summary["overtime"] += float(rec.overtime_hours or 0)
                statuses = {rec.check_in_status, rec.check_out_status}
                if "missed" in statuses:
                    summary["missed"] += 1
                    detail["status"] = "missed"
                elif "absent" in statuses:
                    if leave and scheduled:
                        summary["leave"] += leave
                        summary["unregistered"] += 1 - leave
                        detail["status"] = "leave"
                    else:
                        summary["absent"] += 1
                        detail["status"] = "absent"
                elif "half_day" in statuses:
                    summary["half"] += 1
                    detail["status"] = "half_day"
                    if leave == 0.5 and scheduled:
                        summary["leave"] += 0.5
                    elif leave:
                        summary["conflicts"] += 1
                else:
                    summary["normal"] += 1
                    detail["status"] = "normal"
                    if leave and scheduled:
                        summary["conflicts"] += 1
                if "late" in statuses or "early" in statuses:
                    summary["late"] += 1
            elif scheduled and leave:
                summary["leave"] += leave
                summary["unregistered"] += 1 - leave
                detail["status"] = "leave"
            elif scheduled:
                summary["unregistered"] += 1
            else:
                detail["status"] = "rest"
        details[key] = detail
        day += timedelta(days=1)
    return summary, details


class AttendanceSummaryService:
    def __init__(self, db):
        self.db = db

    async def employees_for_period(self, start, end):
        # Existing records remain visible even after resignation/soft deletion.
        recorded = select(AttendanceRecord.employee_id).where(AttendanceRecord.date.between(start, end))
        q = select(Employee).where(or_(
            Employee.id.in_(recorded),
            (Employee.deleted_at.is_(None)
             & or_(Employee.hire_date.is_(None), Employee.hire_date <= end)
             & or_(Employee.resignation_date >= start,
                   (Employee.resignation_date.is_(None) & (Employee.employment_status == "active")))),
        )).order_by(Employee.employee_no)
        return (await self.db.execute(q)).scalars().unique().all()

    async def load(self, start, end):
        employees = await self.employees_for_period(start, end)
        rules = (await self.db.execute(select(AttendanceRule).where(AttendanceRule.is_active.is_(True))
                                      .order_by(AttendanceRule.updated_at.desc(), AttendanceRule.id))).scalars().all()
        records = (await self.db.execute(select(AttendanceRecord).where(AttendanceRecord.date.between(start, end))
                                        .order_by(AttendanceRecord.date, AttendanceRecord.id))).scalars().all()
        leaves = (await self.db.execute(select(LeaveRequest).where(
            LeaveRequest.status == "approved", LeaveRequest.start_date <= end, LeaveRequest.end_date >= start))).scalars().all()
        result = []
        for emp in employees:
            rule = next((r for r in rules if r.department == emp.department and r.department), None)
            rule = rule or next((r for r in rules if not r.department), None)
            own = [r for r in records if r.employee_id == emp.id]
            summary, days = summarize_employee(emp, start, end, own,
                [l for l in leaves if l.employee_id == emp.id], rule.work_days if rule else None)
            result.append(dict(employee=emp, summary=summary, days=days, records=own))
        return result

    async def monthly(self, month):
        start, end = month_bounds(month)
        rows = await self.load(start, end)
        return dict(month=month, rows=[dict(employee=dict(id=str(r["employee"].id),
            employee_no=r["employee"].employee_no, name=r["employee"].name, department=r["employee"].department),
            summary=r["summary"], days=r["days"], records=[dict(id=str(v.id), employee_id=str(v.employee_id),
            date=v.date.isoformat(), check_in_status=v.check_in_status, check_out_status=v.check_out_status,
            check_in_time=v.check_in_time.isoformat() if v.check_in_time else None,
            check_out_time=v.check_out_time.isoformat() if v.check_out_time else None,
            overtime_hours=float(v.overtime_hours or 0), source=v.source, remark=v.remark) for v in r["records"]]) for r in rows])
