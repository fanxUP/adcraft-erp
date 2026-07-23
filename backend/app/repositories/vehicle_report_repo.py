from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, case, literal_column, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import (
    Vehicle, VehicleDriver, VehicleDispatch, VehicleTripRecord,
    VehicleFuelRecord, VehicleMaintenanceRecord, VehicleCostAllocation,
    VehicleCertificate, VehicleIncident,
)


class VehicleReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 概览统计 ──────────────────────────────────────────────────────────────

    async def get_overview(self, year: int | None = None, month: int | None = None) -> dict:
        """车辆报表概览：车辆总数、本月出车/里程/费用"""
        now = datetime.utcnow()
        y = year or now.year
        m = month or now.month
        month_start = datetime(y, m, 1)
        if m == 12:
            month_end = datetime(y + 1, 1, 1)
        else:
            month_end = datetime(y, m + 1, 1)

        # 车辆总数（未删除、未报废）
        total_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.is_deleted == False,
                Vehicle.status != "scrapped",
            )
        )).scalar() or 0

        # 可用车辆数
        available_vehicles = (await self.db.execute(
            select(func.count()).select_from(Vehicle).where(
                Vehicle.is_deleted == False,
                Vehicle.status == "available",
            )
        )).scalar() or 0

        # 本月出车次数
        month_dispatches = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= month_start,
                VehicleDispatch.created_at < month_end,
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )).scalar() or 0

        # 本月行驶里程
        month_mileage = (await self.db.execute(
            select(func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0)).where(
                VehicleDispatch.actual_return_time >= month_start,
                VehicleDispatch.actual_return_time < month_end,
                VehicleDispatch.status.in_(["returned", "completed"]),
            )
        )).scalar() or 0

        # 本月油费（已审核）
        month_fuel = (await self.db.execute(
            select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
                VehicleFuelRecord.fuel_time >= month_start,
                VehicleFuelRecord.fuel_time < month_end,
                VehicleFuelRecord.status == "approved",
            )
        )).scalar() or 0

        # 本月维修费（已审核）
        month_maintenance = (await self.db.execute(
            select(func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0)).where(
                VehicleMaintenanceRecord.maintenance_date >= month_start,
                VehicleMaintenanceRecord.maintenance_date < month_end,
                VehicleMaintenanceRecord.status == "approved",
            )
        )).scalar() or 0

        # 本月保险年检费
        month_insurance = (await self.db.execute(
            select(func.coalesce(func.sum(VehicleCertificate.amount), 0)).where(
                VehicleCertificate.created_at >= month_start,
                VehicleCertificate.created_at < month_end,
                VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance", "annual_inspection"]),
            )
        )).scalar() or 0

        # 本月违章/事故费用（已处理/已关闭）
        month_incident = (await self.db.execute(
            select(func.coalesce(func.sum(
                VehicleIncident.fine_amount + VehicleIncident.repair_amount
            ), 0)).where(
                VehicleIncident.incident_time >= month_start,
                VehicleIncident.incident_time < month_end,
                VehicleIncident.status.in_(["resolved", "closed"]),
            )
        )).scalar() or 0

        # 本月手动分摊费用
        month_allocation = (await self.db.execute(
            select(func.coalesce(func.sum(VehicleCostAllocation.amount), 0)).where(
                VehicleCostAllocation.allocation_date >= month_start,
                VehicleCostAllocation.allocation_date < month_end,
            )
        )).scalar() or 0

        month_fuel = float(month_fuel)
        month_maintenance = float(month_maintenance)
        month_insurance = float(month_insurance)
        month_incident = float(month_incident)
        month_allocation = float(month_allocation)
        month_total_cost = month_fuel + month_maintenance + month_insurance + month_incident + month_allocation

        return {
            "total_vehicles": total_vehicles,
            "available_vehicles": available_vehicles,
            "month_dispatches": month_dispatches,
            "month_mileage": round(float(month_mileage), 1),
            "month_fuel_cost": round(month_fuel, 2),
            "month_maintenance_cost": round(month_maintenance, 2),
            "month_insurance_cost": round(month_insurance, 2),
            "month_incident_cost": round(month_incident, 2),
            "month_allocation_cost": round(month_allocation, 2),
            "month_total_cost": round(month_total_cost, 2),
            "avg_cost_per_dispatch": round(month_total_cost / month_dispatches, 2) if month_dispatches else 0,
            "avg_cost_per_km": round(month_total_cost / float(month_mileage), 2) if month_mileage else 0,
            "year": y,
            "month": m,
        }

    # ── 按车辆统计费用 ──────────────────────────────────────────────────────

    async def get_costs_by_vehicle(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        """按车辆统计费用"""
        date_start, date_end = self._resolve_date_range(year, month, start_date, end_date)

        # 各车辆油费
        fuel_q = (
            select(
                VehicleFuelRecord.vehicle_id,
                func.coalesce(func.sum(VehicleFuelRecord.amount), 0).label("fuel_cost"),
            )
            .where(VehicleFuelRecord.status == "approved")
        )
        if date_start:
            fuel_q = fuel_q.where(VehicleFuelRecord.fuel_time >= date_start)
        if date_end:
            fuel_q = fuel_q.where(VehicleFuelRecord.fuel_time < date_end)
        fuel_q = fuel_q.group_by(VehicleFuelRecord.vehicle_id)

        # 各车辆维修费
        maint_q = (
            select(
                VehicleMaintenanceRecord.vehicle_id,
                func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0).label("maintenance_cost"),
            )
            .where(VehicleMaintenanceRecord.status == "approved")
        )
        if date_start:
            maint_q = maint_q.where(VehicleMaintenanceRecord.maintenance_date >= date_start)
        if date_end:
            maint_q = maint_q.where(VehicleMaintenanceRecord.maintenance_date < date_end)
        maint_q = maint_q.group_by(VehicleMaintenanceRecord.vehicle_id)

        # 各车辆保险年检费
        cert_q = (
            select(
                VehicleCertificate.vehicle_id,
                func.coalesce(func.sum(VehicleCertificate.amount), 0).label("insurance_cost"),
            )
            .where(VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance", "annual_inspection"]))
        )
        if date_start:
            cert_q = cert_q.where(VehicleCertificate.created_at >= date_start)
        if date_end:
            cert_q = cert_q.where(VehicleCertificate.created_at < date_end)
        cert_q = cert_q.group_by(VehicleCertificate.vehicle_id)

        # 各车辆违章/事故费
        incident_q = (
            select(
                VehicleIncident.vehicle_id,
                func.coalesce(func.sum(VehicleIncident.fine_amount + VehicleIncident.repair_amount), 0).label("incident_cost"),
            )
            .where(VehicleIncident.status.in_(["resolved", "closed"]))
        )
        if date_start:
            incident_q = incident_q.where(VehicleIncident.incident_time >= date_start)
        if date_end:
            incident_q = incident_q.where(VehicleIncident.incident_time < date_end)
        incident_q = incident_q.group_by(VehicleIncident.vehicle_id)

        # 各车辆手动分摊费
        alloc_q = (
            select(
                VehicleCostAllocation.vehicle_id,
                func.coalesce(func.sum(VehicleCostAllocation.amount), 0).label("allocation_cost"),
            )
        )
        if date_start:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date >= date_start)
        if date_end:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date < date_end)
        alloc_q = alloc_q.group_by(VehicleCostAllocation.vehicle_id)

        # 各车辆里程
        mileage_q = (
            select(
                VehicleDispatch.vehicle_id,
                func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0).label("total_mileage"),
                func.count().label("dispatch_count"),
            )
            .where(VehicleDispatch.status.in_(["returned", "completed"]))
        )
        if date_start:
            mileage_q = mileage_q.where(VehicleDispatch.actual_return_time >= date_start)
        if date_end:
            mileage_q = mileage_q.where(VehicleDispatch.actual_return_time < date_end)
        mileage_q = mileage_q.group_by(VehicleDispatch.vehicle_id)

        # 执行查询
        fuel_results = {str(r[0]): float(r[1]) for r in (await self.db.execute(fuel_q)).all()}
        maint_results = {str(r[0]): float(r[1]) for r in (await self.db.execute(maint_q)).all()}
        cert_results = {str(r[0]): float(r[1]) for r in (await self.db.execute(cert_q)).all()}
        incident_results = {str(r[0]): float(r[1]) for r in (await self.db.execute(incident_q)).all()}
        alloc_results = {str(r[0]): float(r[1]) for r in (await self.db.execute(alloc_q)).all()}
        mileage_results = {str(r[0]): (float(r[1]), int(r[2])) for r in (await self.db.execute(mileage_q)).all()}

        # 合并所有车辆 ID
        all_ids = set(fuel_results) | set(maint_results) | set(cert_results) | set(incident_results) | set(alloc_results) | set(mileage_results)

        # 查询车辆信息
        vehicles = {}
        if all_ids:
            v_rows = (await self.db.execute(
                select(Vehicle).where(Vehicle.id.in_([UUID(vid) for vid in all_ids]))
            )).scalars().all()
            vehicles = {str(v.id): v for v in v_rows}

        result = []
        for vid in all_ids:
            v = vehicles.get(vid)
            fuel = fuel_results.get(vid, 0)
            maint = maint_results.get(vid, 0)
            cert = cert_results.get(vid, 0)
            incident = incident_results.get(vid, 0)
            alloc = alloc_results.get(vid, 0)
            total = fuel + maint + cert + incident + alloc
            mileage, dispatch_count = mileage_results.get(vid, (0, 0))
            result.append({
                "vehicle_id": vid,
                "vehicle_name": v.vehicle_name if v else None,
                "plate_number": v.plate_number if v else None,
                "fuel_cost": round(fuel, 2),
                "maintenance_cost": round(maint, 2),
                "insurance_cost": round(cert, 2),
                "incident_cost": round(incident, 2),
                "allocation_cost": round(alloc, 2),
                "total_cost": round(total, 2),
                "total_mileage": round(mileage, 1),
                "dispatch_count": dispatch_count,
                "avg_cost_per_km": round(total / mileage, 2) if mileage else 0,
                "avg_cost_per_dispatch": round(total / dispatch_count, 2) if dispatch_count else 0,
            })

        result.sort(key=lambda x: x["total_cost"], reverse=True)
        return result

    # ── 按司机统计 ──────────────────────────────────────────────────────────

    async def get_costs_by_driver(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        """按司机统计出车次数和里程"""
        date_start, date_end = self._resolve_date_range(year, month, start_date, end_date)

        q = (
            select(
                VehicleDispatch.driver_id,
                func.count().label("dispatch_count"),
                func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0).label("total_mileage"),
            )
            .where(
                VehicleDispatch.driver_id.isnot(None),
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )
        if date_start:
            q = q.where(VehicleDispatch.created_at >= date_start)
        if date_end:
            q = q.where(VehicleDispatch.created_at < date_end)
        q = q.group_by(VehicleDispatch.driver_id)

        rows = (await self.db.execute(q)).all()

        # 查询司机信息
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

    # ── 里程统计 ──────────────────────────────────────────────────────────────

    async def get_mileage_stats(
        self, year: int | None = None, vehicle_id: UUID | None = None,
    ) -> list[dict]:
        """按月统计里程"""
        y = year or datetime.utcnow().year
        start = datetime(y, 1, 1)
        end = datetime(y + 1, 1, 1)

        q = (
            select(
                func.extract("month", VehicleDispatch.actual_return_time).label("month"),
                func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0).label("total_mileage"),
                func.count().label("dispatch_count"),
            )
            .where(
                VehicleDispatch.actual_return_time >= start,
                VehicleDispatch.actual_return_time < end,
                VehicleDispatch.status.in_(["returned", "completed"]),
            )
        )
        if vehicle_id:
            q = q.where(VehicleDispatch.vehicle_id == vehicle_id)
        q = q.group_by(literal_column("month")).order_by(literal_column("month"))

        rows = (await self.db.execute(q)).all()
        return [
            {
                "month": int(r[0]),
                "total_mileage": round(float(r[1]), 1),
                "dispatch_count": int(r[2]),
            }
            for r in rows
        ]

    # ── 派车统计 ──────────────────────────────────────────────────────────────

    async def get_dispatch_stats(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> dict:
        """派车统计：按状态、用途分布"""
        date_start, date_end = self._resolve_date_range(year, month, start_date, end_date)

        # 按状态统计
        status_q = select(
            VehicleDispatch.status,
            func.count().label("count"),
        )
        if date_start:
            status_q = status_q.where(VehicleDispatch.created_at >= date_start)
        if date_end:
            status_q = status_q.where(VehicleDispatch.created_at < date_end)
        status_q = status_q.group_by(VehicleDispatch.status)
        status_rows = (await self.db.execute(status_q)).all()

        # 按用途（关联申请的原因）统计
        reason_q = (
            select(
                VehicleUseRequest.reason,
                func.count().label("count"),
            )
            .join(VehicleDispatch, VehicleDispatch.request_id == VehicleUseRequest.id)
        )
        if date_start:
            reason_q = reason_q.where(VehicleDispatch.created_at >= date_start)
        if date_end:
            reason_q = reason_q.where(VehicleDispatch.created_at < date_end)
        reason_q = reason_q.group_by(VehicleUseRequest.reason)
        reason_rows = (await self.db.execute(reason_q)).all()

        return {
            "by_status": [{"status": r[0], "count": int(r[1])} for r in status_rows],
            "by_reason": [{"reason": r[0], "count": int(r[1])} for r in reason_rows],
        }

    # ── 订单车辆成本 ──────────────────────────────────────────────────────────

    async def get_order_costs(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        """按订单统计车辆运输成本"""
        date_start, date_end = self._resolve_date_range(year, month, start_date, end_date)

        # 通过派车单关联的订单统计
        dispatch_q = (
            select(
                VehicleDispatch.related_order_id,
                func.count().label("dispatch_count"),
                func.coalesce(func.sum(VehicleDispatch.actual_distance_km), 0).label("total_mileage"),
            )
            .where(
                VehicleDispatch.related_order_id.isnot(None),
                VehicleDispatch.status.notin_(["cancelled"]),
            )
        )
        if date_start:
            dispatch_q = dispatch_q.where(VehicleDispatch.created_at >= date_start)
        if date_end:
            dispatch_q = dispatch_q.where(VehicleDispatch.created_at < date_end)
        dispatch_q = dispatch_q.group_by(VehicleDispatch.related_order_id)

        dispatch_rows = (await self.db.execute(dispatch_q)).all()
        order_dispatches = {str(r[0]): {"count": int(r[1]), "mileage": float(r[2])} for r in dispatch_rows}

        # 通过费用分摊关联的订单统计
        alloc_q = (
            select(
                VehicleCostAllocation.related_order_id,
                func.coalesce(func.sum(VehicleCostAllocation.amount), 0).label("total_cost"),
            )
            .where(VehicleCostAllocation.related_order_id.isnot(None))
        )
        if date_start:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date >= date_start)
        if date_end:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date < date_end)
        alloc_q = alloc_q.group_by(VehicleCostAllocation.related_order_id)

        alloc_rows = (await self.db.execute(alloc_q)).all()
        order_allocations = {str(r[0]): float(r[1]) for r in alloc_rows}

        # 合并
        all_order_ids = set(order_dispatches) | set(order_allocations)
        result = []
        for oid in all_order_ids:
            d = order_dispatches.get(oid, {"count": 0, "mileage": 0})
            a = order_allocations.get(oid, 0)
            result.append({
                "order_id": oid,
                "dispatch_count": d["count"],
                "total_mileage": round(d["mileage"], 1),
                "allocated_cost": round(a, 2),
            })
        result.sort(key=lambda x: x["allocated_cost"], reverse=True)
        return result

    # ── 费用类型分析 ──────────────────────────────────────────────────────────

    async def get_cost_by_type(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        """按费用类型统计"""
        date_start, date_end = self._resolve_date_range(year, month, start_date, end_date)

        # 手动分摊费用按类型
        alloc_q = (
            select(
                VehicleCostAllocation.cost_type,
                func.coalesce(func.sum(VehicleCostAllocation.amount), 0).label("amount"),
            )
        )
        if date_start:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date >= date_start)
        if date_end:
            alloc_q = alloc_q.where(VehicleCostAllocation.allocation_date < date_end)
        alloc_q = alloc_q.group_by(VehicleCostAllocation.cost_type)

        alloc_rows = (await self.db.execute(alloc_q)).all()
        result = [{"cost_type": r[0], "amount": round(float(r[1]), 2)} for r in alloc_rows]

        # 补充油费（如果不在分摊里）
        fuel_q = select(func.coalesce(func.sum(VehicleFuelRecord.amount), 0)).where(
            VehicleFuelRecord.status == "approved"
        )
        if date_start:
            fuel_q = fuel_q.where(VehicleFuelRecord.fuel_time >= date_start)
        if date_end:
            fuel_q = fuel_q.where(VehicleFuelRecord.fuel_time < date_end)
        fuel_total = float((await self.db.execute(fuel_q)).scalar() or 0)
        existing_types = {r["cost_type"] for r in result}
        if "fuel" not in existing_types and fuel_total > 0:
            result.append({"cost_type": "fuel", "amount": fuel_total})

        # 补充维修费
        maint_q = select(func.coalesce(func.sum(VehicleMaintenanceRecord.amount), 0)).where(
            VehicleMaintenanceRecord.status == "approved"
        )
        if date_start:
            maint_q = maint_q.where(VehicleMaintenanceRecord.maintenance_date >= date_start)
        if date_end:
            maint_q = maint_q.where(VehicleMaintenanceRecord.maintenance_date < date_end)
        maint_total = float((await self.db.execute(maint_q)).scalar() or 0)
        if "maintenance" not in existing_types and maint_total > 0:
            result.append({"cost_type": "maintenance", "amount": maint_total})

        # 补充保险年检
        cert_q = select(func.coalesce(func.sum(VehicleCertificate.amount), 0)).where(
            VehicleCertificate.certificate_type.in_(["compulsory_insurance", "commercial_insurance", "annual_inspection"])
        )
        if date_start:
            cert_q = cert_q.where(VehicleCertificate.created_at >= date_start)
        if date_end:
            cert_q = cert_q.where(VehicleCertificate.created_at < date_end)
        cert_total = float((await self.db.execute(cert_q)).scalar() or 0)
        if "insurance" not in existing_types and cert_total > 0:
            result.append({"cost_type": "insurance", "amount": cert_total})

        # 补充违章事故
        inc_q = select(func.coalesce(func.sum(VehicleIncident.fine_amount + VehicleIncident.repair_amount), 0)).where(
            VehicleIncident.status.in_(["resolved", "closed"])
        )
        if date_start:
            inc_q = inc_q.where(VehicleIncident.incident_time >= date_start)
        if date_end:
            inc_q = inc_q.where(VehicleIncident.incident_time < date_end)
        inc_total = float((await self.db.execute(inc_q)).scalar() or 0)
        if "incident" not in existing_types and inc_total > 0:
            result.append({"cost_type": "incident", "amount": inc_total})

        result.sort(key=lambda x: x["amount"], reverse=True)
        return result

    # ── 辅助方法 ──────────────────────────────────────────────────────────────

    def _resolve_date_range(
        self, year: int | None, month: int | None,
        start_date: str | None, end_date: str | None,
    ) -> tuple[datetime | None, datetime | None]:
        """解析日期范围"""
        if start_date and end_date:
            return datetime.fromisoformat(start_date), datetime.fromisoformat(end_date)
        if year and month:
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            return start, end
        if year:
            return datetime(year, 1, 1), datetime(year + 1, 1, 1)
        # 默认当月
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)
        return start, end
