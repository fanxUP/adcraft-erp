from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import (
    VehicleUseRequest, VehicleDispatch, VehicleTripRecord,
    VehicleFuelRecord, VehicleMaintenanceRecord, VehicleCostAllocation,
    VehicleCertificate, VehicleIncident,
)
from app.repositories.vehicle_repo import VehicleRepository
from app.services.operation_log_service import (
    log_operation, OBJ_VEHICLE, OBJ_VEHICLE_DRIVER, OBJ_VEHICLE_USE_REQUEST, OBJ_VEHICLE_DISPATCH,
    OBJ_VEHICLE_TRIP_RECORD, OBJ_VEHICLE_FUEL_RECORD, OBJ_VEHICLE_MAINTENANCE_RECORD,
    OBJ_VEHICLE_COST_ALLOCATION, OBJ_VEHICLE_CERTIFICATE, OBJ_VEHICLE_INCIDENT,
    ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE, ACTION_STATUS_CHANGE,
)

from app.services.vehicle_base_service import VehicleServiceBase


class VehicleComplianceService(VehicleServiceBase):
    # ── 保险/年检/证件 ──────────────────────────────────────────────────────────

    async def list_certificates(self, page=1, page_size=20, vehicle_id=None, certificate_type=None, status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_certificates(skip, page_size, vehicle_id, certificate_type, status)
        return [self._certificate_to_dict(r) for r in records], total

    async def get_certificate(self, cert_id: UUID) -> dict | None:
        r = await self.repo.get_certificate_by_id(cert_id)
        return self._certificate_to_dict(r) if r else None

    async def list_expiring_certificates(self, days=30, vehicle_id=None) -> list[dict]:
        records = await self.repo.list_expiring_certificates(days, vehicle_id)
        result = []
        from datetime import datetime
        now = datetime.utcnow()
        for r in records:
            d = self._certificate_to_dict(r)
            # Calculate urgency
            if r.expire_date:
                days_left = (r.expire_date - now).days
                if days_left < 0:
                    d["urgency"] = "expired"
                elif days_left <= 7:
                    d["urgency"] = "urgent"
                else:
                    d["urgency"] = "warning"
                d["days_left"] = days_left
            result.append(d)
        return result

    async def create_certificate(self, data: dict) -> dict:
        from datetime import datetime
        for field in ("vehicle_id", "driver_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
        for date_field in ["start_date", "expire_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        data.setdefault("status", "active")
        r = await self.repo.create_certificate(data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_CERTIFICATE, object_id=r.id,
            action=ACTION_CREATE, ip_address=self.ip_address,
            after_data=self._certificate_to_dict(r),
        )
        return self._certificate_to_dict(r)

    async def update_certificate(self, cert_id: UUID, data: dict) -> dict:
        from datetime import datetime
        r = await self.repo.get_certificate_by_id(cert_id)
        if not r:
            raise ValueError("证件记录不存在")
        before = self._certificate_to_dict(r)
        for field in ("vehicle_id", "driver_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
        for date_field in ["start_date", "expire_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        r = await self.repo.update_certificate(r, data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_CERTIFICATE, object_id=r.id,
            action=ACTION_UPDATE, ip_address=self.ip_address,
            before_data=before, after_data=self._certificate_to_dict(r),
        )
        return self._certificate_to_dict(r)

    async def delete_certificate(self, cert_id: UUID) -> None:
        r = await self.repo.get_certificate_by_id(cert_id)
        if not r:
            raise ValueError("证件记录不存在")
        before = self._certificate_to_dict(r)
        await self.repo.delete_certificate(r)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_CERTIFICATE, object_id=cert_id,
            action=ACTION_DELETE, ip_address=self.ip_address,
            before_data=before,
        )

    def _certificate_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "vehicle_id": str(r.vehicle_id) if r.vehicle_id else None,
            "vehicle_name": r.vehicle.vehicle_name if r.vehicle else None,
            "plate_number": r.vehicle.plate_number if r.vehicle else None,
            "driver_id": str(r.driver_id) if r.driver_id else None,
            "driver_name": r.driver.driver_name if r.driver else None,
            "certificate_type": r.certificate_type,
            "certificate_no": r.certificate_no,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "expire_date": r.expire_date.isoformat() if r.expire_date else None,
            "amount": float(r.amount) if r.amount else 0,
            "file_url": r.file_url,
            "reminder_days": r.reminder_days,
            "status": r.status,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    # ── 违章/事故/异常 ──────────────────────────────────────────────────────────

    async def list_incidents(self, page=1, page_size=20, vehicle_id=None, incident_type=None, status=None, driver_id=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_incidents(skip, page_size, vehicle_id, incident_type, status, driver_id)
        return [self._incident_to_dict(r) for r in records], total

    async def get_incident(self, incident_id: UUID) -> dict | None:
        r = await self.repo.get_incident_by_id(incident_id)
        return self._incident_to_dict(r) if r else None

    async def create_incident(self, data: dict) -> dict:
        from datetime import datetime
        for field in ("vehicle_id", "driver_id", "dispatch_id", "related_order_id", "related_install_task_id", "responsible_user_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
        for date_field in ["incident_time"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        data.setdefault("status", "pending")
        r = await self.repo.create_incident(data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_INCIDENT, object_id=r.id,
            action=ACTION_CREATE, ip_address=self.ip_address,
            after_data=self._incident_to_dict(r),
        )
        return self._incident_to_dict(r)

    async def update_incident(self, incident_id: UUID, data: dict) -> dict:
        from datetime import datetime
        r = await self.repo.get_incident_by_id(incident_id)
        if not r:
            raise ValueError("异常记录不存在")
        before = self._incident_to_dict(r)
        for field in ("vehicle_id", "driver_id", "dispatch_id", "related_order_id", "related_install_task_id", "responsible_user_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
        for date_field in ["incident_time"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        r = await self.repo.update_incident(r, data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_INCIDENT, object_id=r.id,
            action=ACTION_UPDATE, ip_address=self.ip_address,
            before_data=before, after_data=self._incident_to_dict(r),
        )
        return self._incident_to_dict(r)

    async def resolve_incident(self, incident_id: UUID, resolution: str, status: str = "resolved") -> dict:
        r = await self.repo.get_incident_by_id(incident_id)
        if not r:
            raise ValueError("异常记录不存在")
        if r.status in ("closed",):
            raise ValueError("已关闭的异常不可处理")
        before = self._incident_to_dict(r)
        r.status = status
        r.resolution = resolution
        await self.db.flush()
        await self.db.refresh(r)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_INCIDENT, object_id=r.id,
            action=ACTION_STATUS_CHANGE, ip_address=self.ip_address,
            before_data=before, after_data=self._incident_to_dict(r),
        )
        return self._incident_to_dict(r)

    async def delete_incident(self, incident_id: UUID) -> None:
        r = await self.repo.get_incident_by_id(incident_id)
        if not r:
            raise ValueError("异常记录不存在")
        before = self._incident_to_dict(r)
        await self.repo.delete_incident(r)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_INCIDENT, object_id=incident_id,
            action=ACTION_DELETE, ip_address=self.ip_address,
            before_data=before,
        )

    def _incident_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "vehicle_id": str(r.vehicle_id) if r.vehicle_id else None,
            "vehicle_name": r.vehicle.vehicle_name if r.vehicle else None,
            "plate_number": r.vehicle.plate_number if r.vehicle else None,
            "driver_id": str(r.driver_id) if r.driver_id else None,
            "driver_name": r.driver.driver_name if r.driver else None,
            "dispatch_id": str(r.dispatch_id) if r.dispatch_id else None,
            "dispatch_no": r.dispatch.dispatch_no if r.dispatch else None,
            "related_order_id": str(r.related_order_id) if r.related_order_id else None,
            "related_install_task_id": str(r.related_install_task_id) if r.related_install_task_id else None,
            "incident_type": r.incident_type,
            "incident_time": r.incident_time.isoformat() if r.incident_time else None,
            "location": r.location,
            "description": r.description,
            "fine_amount": float(r.fine_amount) if r.fine_amount else 0,
            "points_deducted": r.points_deducted or 0,
            "repair_amount": float(r.repair_amount) if r.repair_amount else 0,
            "responsible_user_id": str(r.responsible_user_id) if r.responsible_user_id else None,
            "responsible_user_name": r.responsible_user.real_name if r.responsible_user else None,
            "status": r.status,
            "resolution": r.resolution,
            "evidence_url": r.evidence_url,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
