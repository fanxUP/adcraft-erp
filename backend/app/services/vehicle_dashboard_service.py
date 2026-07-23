from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import (
    Vehicle, VehicleDriver, VehicleDispatch, VehicleUseRequest,
    VehicleFuelRecord, VehicleMaintenanceRecord, VehicleCertificate,
    VehicleIncident, VehicleCostAllocation,
)
from app.models.user import User


class VehicleDashboardService:
    def __init__(self, db: AsyncSession, current_user: User | None = None):
        self.db = db
        self.current_user = current_user

    # ── 首页 14 项指标 ────────────────────────────────────────────────────────

    async def get_overview(self) -> dict:
        """车辆管理首页：14 项核心指标"""
        now = datetime.utcnow()
        today = now.date()
        today_start = datetime(today.year, today.month, today.day)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        month_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1)
        else:
            month_end = datetime(now.year, now.month + 1, 1)

        # 1. 车辆总数（未删除、未报废）
        total_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.deleted_at.is_(None),
                Vehicle.status != "scrapped",
            )
        )).scalar() or 0

        # 2. 可用车辆
        available_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.deleted_at.is_(None),
                Vehicle.status == "available",
            )
        )).scalar() or 0

        # 3. 使用中车辆（assigned + in_use）
        in_use_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.deleted_at.is_(None),
                Vehicle.status.in_(["assigned", "in_use"]),
            )
        )).scalar() or 0

        # 4. 维修中车辆
        maintenance_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.deleted_at.is_(None),
                Vehicle.status == "maintenance",
            )
        )).scalar() or 0

        # 5. 停用车辆
        disabled_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.deleted_at.is_(None),
                Vehicle.status == "disabled",
            )
        )).scalar() or 0

        # 6. 今日出车次数
        today_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= today_start,
                VehicleDispatch.created_at <= today_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 7. 今日待收车（状态为 dispatched/in_use）
        pending_return = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.status.in_(["dispatched", "in_use"]),
            )
        )).scalar() or 0

        # 8. 今日异常
        today_incidents = (await self.db.execute(
            select(func.count()).select_from(VehicleIncident).where(
                VehicleIncident.incident_time >= today_start,
                VehicleIncident.incident_time <= today_end,
            )
        )).scalar() or 0

        # 9. 本月油费（已审核）
        month_fuel = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
                VehicleFuelRecord.fuel_time >= month_start,
                VehicleFuelRecord.fuel_time < month_end,
                VehicleFuelRecord.status == "approved",
            )
        )).scalar() or 0)

        # 10. 本月维修费（已审核）
        month_maintenance = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0)).where(
                VehicleMaintenanceRecord.maintenance_date >= month_start,
                VehicleMaintenanceRecord.maintenance_date < month_end,
                VehicleMaintenanceRecord.status == "approved",
            )
        )).scalar() or 0)

        # 11. 本月车辆总费用
        month_insurance = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCertificate.amount), 0)).where(
                VehicleCertificate.created_at >= month_start,
                VehicleCertificate.created_at < month_end,
                VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance", "annual_inspection"]),
            )
        )).scalar() or 0)

        month_incident = float((await self.db.execute(
            select(func.coalesce(func.sum(
                VehicleIncident.fine_amount + VehicleIncident.repair_amount
            ), 0)).where(
                VehicleIncident.incident_time >= month_start,
                VehicleIncident.incident_time < month_end,
                VehicleIncident.status.in_(["resolved", "closed"]),
            )
        )).scalar() or 0)

        month_allocation = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCostAllocation.amount), 0)).where(
                VehicleCostAllocation.allocation_date >= month_start,
                VehicleCostAllocation.allocation_date < month_end,
            )
        )).scalar() or 0)

        month_total = month_fuel + month_maintenance + month_insurance + month_incident + month_allocation

        # 12. 即将保险到期（30 天内）
        soon = now + timedelta(days=30)
        expiring_insurance = (await self.db.execute(
            select(func.count()).select_from(VehicleCertificate).where(
                VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance"]),
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= soon,
                VehicleCertificate.expire_date >= now,
            )
        )).scalar() or 0

        # 13. 即将年检到期（30 天内）
        expiring_inspection = (await self.db.execute(
            select(func.count()).select_from(VehicleCertificate).where(
                VehicleCertificate.certificate_type == "annual_inspection",
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= soon,
                VehicleCertificate.expire_date >= now,
            )
        )).scalar() or 0

        # 14. 驾驶证即将到期（30 天内）
        expiring_license = (await self.db.execute(
            select(func.count()).select_from(VehicleDriver).where(
                VehicleDriver.deleted_at.is_(None),
                VehicleDriver.license_expire_date.isnot(None),
                VehicleDriver.license_expire_date <= soon,
                VehicleDriver.license_expire_date >= now,
            )
        )).scalar() or 0

        return {
            "total_vehicles": total_vehicles,
            "available_vehicles": available_vehicles,
            "in_use_vehicles": in_use_vehicles,
            "maintenance_vehicles": maintenance_vehicles,
            "disabled_vehicles": disabled_vehicles,
            "today_dispatches": today_dispatches,
            "pending_return": pending_return,
            "today_incidents": today_incidents,
            "month_fuel_cost": round(month_fuel, 2),
            "month_maintenance_cost": round(month_maintenance, 2),
            "month_total_cost": round(month_total, 2),
            "expiring_insurance": expiring_insurance,
            "expiring_inspection": expiring_inspection,
            "expiring_license": expiring_license,
        }

    # ── 今日统计 ──────────────────────────────────────────────────────────────

    async def get_today_stats(self) -> dict:
        """今日派车、待收车、异常、油费"""
        now = datetime.utcnow()
        today = now.date()
        today_start = datetime(today.year, today.month, today.day)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

        # 今日派车列表
        dispatches_result = await self.db.execute(
            select(VehicleDispatch).where(
                VehicleDispatch.created_at >= today_start,
                VehicleDispatch.created_at <= today_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            ).order_by(VehicleDispatch.created_at.desc())
        )
        dispatches = dispatches_result.scalars().all()

        # 待收车列表
        pending_result = await self.db.execute(
            select(VehicleDispatch).where(
                VehicleDispatch.status.in_(["dispatched", "in_use"]),
            ).order_by(VehicleDispatch.planned_return_time.asc())
        )
        pending = pending_result.scalars().all()

        # 今日异常
        incidents_result = await self.db.execute(
            select(VehicleIncident).where(
                VehicleIncident.incident_time >= today_start,
                VehicleIncident.incident_time <= today_end,
            ).order_by(VehicleIncident.incident_time.desc())
        )
        incidents = incidents_result.scalars().all()

        # 今日油费
        today_fuel = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
                VehicleFuelRecord.fuel_time >= today_start,
                VehicleFuelRecord.fuel_time <= today_end,
                VehicleFuelRecord.status == "approved",
            )
        )).scalar() or 0)

        # 今日其他费用
        today_other = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCostAllocation.amount), 0)).where(
                VehicleCostAllocation.allocation_date >= today_start,
                VehicleCostAllocation.allocation_date <= today_end,
            )
        )).scalar() or 0)

        # 明日预计用车（已批准的申请，计划明天出车）
        tomorrow = today + timedelta(days=1)
        tomorrow_start = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
        tomorrow_end = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59)
        tomorrow_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.planned_start_time >= tomorrow_start,
                VehicleDispatch.planned_start_time <= tomorrow_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 即将到期提醒
        soon = now + timedelta(days=30)
        reminders_count = (await self.db.execute(
            select(func.count()).select_from(VehicleCertificate).where(
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= soon,
                VehicleCertificate.expire_date >= now,
            )
        )).scalar() or 0
        license_reminders = (await self.db.execute(
            select(func.count()).select_from(VehicleDriver).where(
                VehicleDriver.deleted_at.is_(None),
                VehicleDriver.license_expire_date.isnot(None),
                VehicleDriver.license_expire_date <= soon,
                VehicleDriver.license_expire_date >= now,
            )
        )).scalar() or 0

        def _serialize_dispatch(d: VehicleDispatch) -> dict:
            return {
                "id": str(d.id),
                "vehicle_id": str(d.vehicle_id) if d.vehicle_id else None,
                "driver_id": str(d.driver_id) if d.driver_id else None,
                "status": d.status,
                "purpose": d.purpose,
                "destination": d.destination,
                "planned_start_time": d.planned_start_time.isoformat() if d.planned_start_time else None,
                "planned_return_time": d.planned_return_time.isoformat() if d.planned_return_time else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }

        def _serialize_incident(i: VehicleIncident) -> dict:
            return {
                "id": str(i.id),
                "vehicle_id": str(i.vehicle_id) if i.vehicle_id else None,
                "incident_type": i.incident_type,
                "description": i.description,
                "severity": i.severity,
                "status": i.status,
                "incident_time": i.incident_time.isoformat() if i.incident_time else None,
            }

        return {
            "today_dispatches_count": len(dispatches),
            "pending_return_count": len(pending),
            "today_incidents_count": len(incidents),
            "today_fuel_cost": round(today_fuel, 2),
            "today_other_cost": round(today_other, 2),
            "tomorrow_dispatches": tomorrow_dispatches,
            "reminders_count": reminders_count + license_reminders,
            "dispatches": [_serialize_dispatch(d) for d in dispatches],
            "pending_returns": [_serialize_dispatch(d) for d in pending],
            "incidents": [_serialize_incident(i) for i in incidents],
        }

    # ── 本月费用明细 ──────────────────────────────────────────────────────────

    async def get_monthly_costs(self) -> dict:
        """本月各项费用明细"""
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1)
        else:
            month_end = datetime(now.year, now.month + 1, 1)

        month_fuel = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
                VehicleFuelRecord.fuel_time >= month_start,
                VehicleFuelRecord.fuel_time < month_end,
                VehicleFuelRecord.status == "approved",
            )
        )).scalar() or 0)

        month_maintenance = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0)).where(
                VehicleMaintenanceRecord.maintenance_date >= month_start,
                VehicleMaintenanceRecord.maintenance_date < month_end,
                VehicleMaintenanceRecord.status == "approved",
            )
        )).scalar() or 0)

        month_insurance = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCertificate.amount), 0)).where(
                VehicleCertificate.created_at >= month_start,
                VehicleCertificate.created_at < month_end,
                VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance", "annual_inspection"]),
            )
        )).scalar() or 0)

        month_incident = float((await self.db.execute(
            select(func.coalesce(func.sum(
                VehicleIncident.fine_amount + VehicleIncident.repair_amount
            ), 0)).where(
                VehicleIncident.incident_time >= month_start,
                VehicleIncident.incident_time < month_end,
                VehicleIncident.status.in_(["resolved", "closed"]),
            )
        )).scalar() or 0)

        month_allocation = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCostAllocation.amount), 0)).where(
                VehicleCostAllocation.allocation_date >= month_start,
                VehicleCostAllocation.allocation_date < month_end,
            )
        )).scalar() or 0)

        month_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= month_start,
                VehicleDispatch.created_at < month_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        month_mileage = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0)).where(
                VehicleDispatch.actual_return_time >= month_start,
                VehicleDispatch.actual_return_time < month_end,
                VehicleDispatch.status.in_(["returned", "completed"]),
            )
        )).scalar() or 0)

        total = month_fuel + month_maintenance + month_insurance + month_incident + month_allocation

        return {
            "year": now.year,
            "month": now.month,
            "fuel_cost": round(month_fuel, 2),
            "maintenance_cost": round(month_maintenance, 2),
            "insurance_cost": round(month_insurance, 2),
            "incident_cost": round(month_incident, 2),
            "allocation_cost": round(month_allocation, 2),
            "total_cost": round(total, 2),
            "dispatch_count": month_dispatches,
            "total_mileage": round(month_mileage, 1),
            "avg_cost_per_dispatch": round(total / month_dispatches, 2) if month_dispatches else 0,
        }

    # ── 到期提醒 ──────────────────────────────────────────────────────────────

    async def get_reminders(self) -> dict:
        """保险、年检、驾驶证到期提醒"""
        now = datetime.utcnow()
        soon = now + timedelta(days=30)
        far = now + timedelta(days=90)

        # 保险到期
        insurance_q = (
            select(VehicleCertificate, Vehicle.plate_number, Vehicle.vehicle_name)
            .join(Vehicle, VehicleCertificate.vehicle_id == Vehicle.id)
            .where(
                VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance"]),
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= far,
                Vehicle.deleted_at.is_(None),
            )
            .order_by(VehicleCertificate.expire_date.asc())
        )
        insurance_rows = (await self.db.execute(insurance_q)).all()

        # 年检到期
        inspection_q = (
            select(VehicleCertificate, Vehicle.plate_number, Vehicle.vehicle_name)
            .join(Vehicle, VehicleCertificate.vehicle_id == Vehicle.id)
            .where(
                VehicleCertificate.certificate_type == "annual_inspection",
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= far,
                Vehicle.deleted_at.is_(None),
            )
            .order_by(VehicleCertificate.expire_date.asc())
        )
        inspection_rows = (await self.db.execute(inspection_q)).all()

        # 驾驶证到期
        license_q = (
            select(VehicleDriver).where(
                VehicleDriver.deleted_at.is_(None),
                VehicleDriver.license_expire_date.isnot(None),
                VehicleDriver.license_expire_date <= far,
            ).order_by(VehicleDriver.license_expire_date.asc())
        )
        license_rows = (await self.db.execute(license_q)).scalars().all()

        def _urgency(expiry_date: datetime) -> str:
            if expiry_date <= now:
                return "expired"
            if expiry_date <= soon:
                return "urgent"
            return "warning"

        def _serialize_cert(row) -> dict:
            cert = row[0]
            return {
                "id": str(cert.id),
                "vehicle_id": str(cert.vehicle_id),
                "plate_number": row[1],
                "vehicle_name": row[2],
                "certificate_type": cert.certificate_type,
                "certificate_no": cert.certificate_no,
                "expiry_date": cert.expire_date.isoformat() if cert.expire_date else None,
                "urgency": _urgency(cert.expire_date) if cert.expire_date else "unknown",
            }

        return {
            "insurance": [_serialize_cert(r) for r in insurance_rows],
            "inspection": [_serialize_cert(r) for r in inspection_rows],
            "license": [
                {
                    "id": str(d.id),
                    "driver_name": d.driver_name,
                    "phone": d.phone,
                    "license_no": d.license_no,
                    "license_expiry": d.license_expire_date.isoformat() if d.license_expire_date else None,
                    "urgency": _urgency(d.license_expire_date) if d.license_expire_date else "unknown",
                }
                for d in license_rows
            ],
        }

    # ── 老板日报车辆部分 ──────────────────────────────────────────────────────

    async def get_daily_report(self, report_date: str | None = None) -> dict:
        """老板日报：车辆与安装运输部分"""
        if report_date:
            d = datetime.fromisoformat(report_date)
        else:
            d = datetime.utcnow()
        day_start = datetime(d.year, d.month, d.day)
        day_end = datetime(d.year, d.month, d.day, 23, 59, 59)
        tomorrow = d.date() + timedelta(days=1)
        tomorrow_start = datetime(tomorrow.year, tomorrow.month, tomorrow.day)
        tomorrow_end = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59)

        # 今日出车
        today_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= day_start,
                VehicleDispatch.created_at <= day_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 今日安装关联派车
        install_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= day_start,
                VehicleDispatch.created_at <= day_end,
                VehicleDispatch.related_install_task_id.isnot(None),
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 今日未收车（截至查询时刻仍在路上的）
        pending_return = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.status.in_(["dispatched", "in_use"]),
            )
        )).scalar() or 0

        # 今日车辆异常
        today_incidents = (await self.db.execute(
            select(func.count()).select_from(VehicleIncident).where(
                VehicleIncident.incident_time >= day_start,
                VehicleIncident.incident_time <= day_end,
            )
        )).scalar() or 0

        # 今日油费
        today_fuel = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
                VehicleFuelRecord.fuel_time >= day_start,
                VehicleFuelRecord.fuel_time <= day_end,
                VehicleFuelRecord.status == "approved",
            )
        )).scalar() or 0)

        # 今日其他车辆费用
        today_other = float((await self.db.execute(
            select(func.coalesce(func.sum(VehicleCostAllocation.amount), 0)).where(
                VehicleCostAllocation.allocation_date >= day_start,
                VehicleCostAllocation.allocation_date <= day_end,
            )
        )).scalar() or 0)

        # 明日预计用车
        tomorrow_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.planned_start_time >= tomorrow_start,
                VehicleDispatch.planned_start_time <= tomorrow_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 即将到期提醒
        now = datetime.utcnow()
        soon = now + timedelta(days=30)
        cert_reminders = (await self.db.execute(
            select(func.count()).select_from(VehicleCertificate).where(
                VehicleCertificate.expire_date.isnot(None),
                VehicleCertificate.expire_date <= soon,
                VehicleCertificate.expire_date >= now,
            )
        )).scalar() or 0
        license_reminders = (await self.db.execute(
            select(func.count()).select_from(VehicleDriver).where(
                VehicleDriver.deleted_at.is_(None),
                VehicleDriver.license_expire_date.isnot(None),
                VehicleDriver.license_expire_date <= soon,
                VehicleDriver.license_expire_date >= now,
            )
        )).scalar() or 0

        return {
            "date": d.strftime("%Y-%m-%d"),
            "today_dispatches": today_dispatches,
            "install_dispatches": install_dispatches,
            "pending_return": pending_return,
            "today_incidents": today_incidents,
            "today_fuel_cost": round(today_fuel, 2),
            "today_other_cost": round(today_other, 2),
            "tomorrow_dispatches": tomorrow_dispatches,
            "reminders_count": cert_reminders + license_reminders,
        }

    # ── 费用排行 ──────────────────────────────────────────────────────────────

    async def get_expense_ranking(self, year: int | None = None, month: int | None = None) -> list[dict]:
        """单车费用排行"""
        now = datetime.utcnow()
        y = year or now.year
        m = month or now.month
        month_start = datetime(y, m, 1)
        if m == 12:
            month_end = datetime(y + 1, 1, 1)
        else:
            month_end = datetime(y, m + 1, 1)

        # 油费
        fuel_q = (
            select(
                VehicleFuelRecord.vehicle_id,
                func.coalesce(func.sum(VehicleFuelRecord.amount), 0).label("fuel_cost"),
            )
            .where(
                VehicleFuelRecord.fuel_time >= month_start,
                VehicleFuelRecord.fuel_time < month_end,
                VehicleFuelRecord.status == "approved",
            )
            .group_by(VehicleFuelRecord.vehicle_id)
        )

        # 维修费
        maint_q = (
            select(
                VehicleMaintenanceRecord.vehicle_id,
                func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0).label("maint_cost"),
            )
            .where(
                VehicleMaintenanceRecord.maintenance_date >= month_start,
                VehicleMaintenanceRecord.maintenance_date < month_end,
                VehicleMaintenanceRecord.status == "approved",
            )
            .group_by(VehicleMaintenanceRecord.vehicle_id)
        )

        fuel_rows = {str(r[0]): float(r[1]) for r in (await self.db.execute(fuel_q)).all()}
        maint_rows = {str(r[0]): float(r[1]) for r in (await self.db.execute(maint_q)).all()}

        all_ids = set(fuel_rows) | set(maint_rows)
        if not all_ids:
            return []

        vehicles = {}
        v_rows = (await self.db.execute(
            select(Vehicle).where(Vehicle.id.in_([UUID(vid) for vid in all_ids]))
        )).scalars().all()
        vehicles = {str(v.id): v for v in v_rows}

        result = []
        for vid in all_ids:
            v = vehicles.get(vid)
            fuel = fuel_rows.get(vid, 0)
            maint = maint_rows.get(vid, 0)
            result.append({
                "vehicle_id": vid,
                "plate_number": v.plate_number if v else None,
                "vehicle_name": v.vehicle_name if v else None,
                "fuel_cost": round(fuel, 2),
                "maintenance_cost": round(maint, 2),
                "total_cost": round(fuel + maint, 2),
            })

        result.sort(key=lambda x: x["total_cost"], reverse=True)
        return result

    # ── 司机出车排行 ──────────────────────────────────────────────────────────

    async def get_driver_ranking(self, year: int | None = None, month: int | None = None) -> list[dict]:
        """司机出车排行"""
        now = datetime.utcnow()
        y = year or now.year
        m = month or now.month
        month_start = datetime(y, m, 1)
        if m == 12:
            month_end = datetime(y + 1, 1, 1)
        else:
            month_end = datetime(y, m + 1, 1)

        q = (
            select(
                VehicleDispatch.driver_id,
                func.count().label("dispatch_count"),
                func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0).label("total_mileage"),
            )
            .where(
                VehicleDispatch.driver_id.isnot(None),
                VehicleDispatch.created_at >= month_start,
                VehicleDispatch.created_at < month_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
            .group_by(VehicleDispatch.driver_id)
        )

        rows = (await self.db.execute(q)).all()
        if not rows:
            return []

        driver_ids = [r[0] for r in rows if r[0]]
        drivers = {}
        if driver_ids:
            d_rows = (await self.db.execute(
                select(VehicleDriver).where(VehicleDriver.id.in_(driver_ids))
            )).scalars().all()
            drivers = {str(d.id): d for d in d_rows}

        result = []
        for r in rows:
            did = str(r[0]) if r[0] else None
            d = drivers.get(did)
            result.append({
                "driver_id": did,
                "driver_name": d.driver_name if d else None,
                "phone": d.phone if d else None,
                "dispatch_count": int(r[1]),
                "total_mileage": round(float(r[2]), 1),
            })

        result.sort(key=lambda x: x["dispatch_count"], reverse=True)
        return result
