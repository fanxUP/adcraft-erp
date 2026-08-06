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


class VehicleFinanceService(VehicleServiceBase):
    # ── 油费记录 ──────────────────────────────────────────────────────────────────

    async def list_fuel_records(self, page=1, page_size=20, vehicle_id=None, driver_id=None, status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_fuel_records(skip, page_size, vehicle_id, driver_id, status)
        return [self._fuel_to_dict(r) for r in records], total

    async def get_fuel_record(self, record_id: UUID) -> dict | None:
        r = await self.repo.get_fuel_record_by_id(record_id)
        return self._fuel_to_dict(r) if r else None

    async def create_fuel_record(self, data: dict) -> dict:
        from datetime import datetime
        self._coerce_uuid_fields(data, ("vehicle_id", "driver_id", "dispatch_id", "payer_id"))
        for date_field in ["fuel_time"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        data.setdefault("status", "pending_review")
        r = await self.repo.create_fuel_record(data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_FUEL_RECORD, object_id=r.id,
            action=ACTION_CREATE, ip_address=self.ip_address,
            after_data=self._fuel_to_dict(r),
        )
        return self._fuel_to_dict(r)

    async def update_fuel_record(self, record_id: UUID, data: dict) -> dict:
        from datetime import datetime
        r = await self.repo.get_fuel_record_by_id(record_id)
        if not r:
            raise ValueError("油费记录不存在")
        if r.status not in ("pending_review", "rejected"):
            raise ValueError("只有待审核或已驳回的记录可以编辑")
        before = self._fuel_to_dict(r)
        self._coerce_uuid_fields(data, ("vehicle_id", "driver_id", "dispatch_id", "payer_id"))
        for date_field in ["fuel_time"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        r = await self.repo.update_fuel_record(r, data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_FUEL_RECORD, object_id=r.id,
            action=ACTION_UPDATE, ip_address=self.ip_address,
            before_data=before, after_data=self._fuel_to_dict(r),
        )
        return self._fuel_to_dict(r)

    async def review_fuel_record(self, record_id: UUID, status: str, remark: str | None = None) -> dict:
        r = await self.repo.get_fuel_record_by_id(record_id)
        if not r:
            raise ValueError("油费记录不存在")
        if r.status != "pending_review":
            raise ValueError("只有待审核的记录可以审核")
        if status not in ("approved", "rejected"):
            raise ValueError("审核状态只能是 approved 或 rejected")
        before = self._fuel_to_dict(r)
        r.status = status
        if remark:
            r.remark = remark
        await self.db.flush()
        await self.db.refresh(r)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_FUEL_RECORD, object_id=r.id,
            action=ACTION_STATUS_CHANGE, ip_address=self.ip_address,
            before_data=before, after_data=self._fuel_to_dict(r),
        )
        return self._fuel_to_dict(r)

    def _fuel_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "vehicle_id": str(r.vehicle_id) if r.vehicle_id else None,
            "vehicle_name": r.vehicle.vehicle_name if r.vehicle else None,
            "plate_number": r.vehicle.plate_number if r.vehicle else None,
            "driver_id": str(r.driver_id) if r.driver_id else None,
            "driver_name": r.driver.driver_name if r.driver else None,
            "dispatch_id": str(r.dispatch_id) if r.dispatch_id else None,
            "dispatch_no": r.dispatch.dispatch_no if r.dispatch else None,
            "fuel_time": r.fuel_time.isoformat() if r.fuel_time else None,
            "amount": float(r.amount) if r.amount else 0,
            "liters": float(r.liters) if r.liters else None,
            "unit_price": float(r.unit_price) if r.unit_price else None,
            "gas_station": r.gas_station,
            "mileage": float(r.mileage) if r.mileage else None,
            "payment_method": r.payment_method,
            "payer_id": str(r.payer_id) if r.payer_id else None,
            "payer_name": r.payer.real_name if r.payer else None,
            "is_driver_advance": r.is_driver_advance,
            "receipt_url": r.receipt_url,
            "status": r.status,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    # ── 维修保养记录 ──────────────────────────────────────────────────────────────

    async def list_maintenance_records(self, page=1, page_size=20, vehicle_id=None, maintenance_type=None, status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_maintenance_records(skip, page_size, vehicle_id, maintenance_type, status)
        return [self._maintenance_to_dict(r) for r in records], total

    async def get_maintenance_record(self, record_id: UUID) -> dict | None:
        r = await self.repo.get_maintenance_record_by_id(record_id)
        return self._maintenance_to_dict(r) if r else None

    async def create_maintenance_record(self, data: dict) -> dict:
        from datetime import datetime
        self._coerce_uuid_fields(data, ("vehicle_id", "handler_id"))
        for date_field in ["maintenance_date", "next_maintenance_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        data.setdefault("status", "pending_review")
        r = await self.repo.create_maintenance_record(data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_MAINTENANCE_RECORD, object_id=r.id,
            action=ACTION_CREATE, ip_address=self.ip_address,
            after_data=self._maintenance_to_dict(r),
        )
        return self._maintenance_to_dict(r)

    async def update_maintenance_record(self, record_id: UUID, data: dict) -> dict:
        from datetime import datetime
        r = await self.repo.get_maintenance_record_by_id(record_id)
        if not r:
            raise ValueError("维修保养记录不存在")
        if r.status not in ("pending_review", "rejected"):
            raise ValueError("只有待审核或已驳回的记录可以编辑")
        before = self._maintenance_to_dict(r)
        self._coerce_uuid_fields(data, ("vehicle_id", "handler_id"))
        for date_field in ["maintenance_date", "next_maintenance_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        r = await self.repo.update_maintenance_record(r, data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_MAINTENANCE_RECORD, object_id=r.id,
            action=ACTION_UPDATE, ip_address=self.ip_address,
            before_data=before, after_data=self._maintenance_to_dict(r),
        )
        return self._maintenance_to_dict(r)

    async def review_maintenance_record(self, record_id: UUID, status: str, remark: str | None = None) -> dict:
        r = await self.repo.get_maintenance_record_by_id(record_id)
        if not r:
            raise ValueError("维修保养记录不存在")
        if r.status != "pending_review":
            raise ValueError("只有待审核的记录可以审核")
        if status not in ("approved", "rejected"):
            raise ValueError("审核状态只能是 approved 或 rejected")
        before = self._maintenance_to_dict(r)
        r.status = status
        if remark:
            r.remark = remark
        await self.db.flush()
        await self.db.refresh(r)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_MAINTENANCE_RECORD, object_id=r.id,
            action=ACTION_STATUS_CHANGE, ip_address=self.ip_address,
            before_data=before, after_data=self._maintenance_to_dict(r),
        )
        return self._maintenance_to_dict(r)

    def _maintenance_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "vehicle_id": str(r.vehicle_id) if r.vehicle_id else None,
            "vehicle_name": r.vehicle.vehicle_name if r.vehicle else None,
            "plate_number": r.vehicle.plate_number if r.vehicle else None,
            "maintenance_type": r.maintenance_type,
            "maintenance_date": r.maintenance_date.isoformat() if r.maintenance_date else None,
            "maintenance_item": r.maintenance_item,
            "repair_shop": r.repair_shop,
            "amount": float(r.amount) if r.amount else 0,
            "mileage": float(r.mileage) if r.mileage else None,
            "next_maintenance_mileage": float(r.next_maintenance_mileage) if r.next_maintenance_mileage else None,
            "next_maintenance_date": r.next_maintenance_date.isoformat() if r.next_maintenance_date else None,
            "handler_id": str(r.handler_id) if r.handler_id else None,
            "handler_name": r.handler.real_name if r.handler else None,
            "invoice_url": r.invoice_url,
            "before_photo_url": r.before_photo_url,
            "after_photo_url": r.after_photo_url,
            "status": r.status,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    # ── 通用费用 ──────────────────────────────────────────────────────────────────

    async def list_cost_allocations(self, page=1, page_size=20, vehicle_id=None, cost_type=None, source_type=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_cost_allocations(skip, page_size, vehicle_id, cost_type, source_type)
        return [self._cost_to_dict(r) for r in records], total

    async def get_cost_allocation(self, cost_id: UUID) -> dict | None:
        r = await self.repo.get_cost_allocation_by_id(cost_id)
        return self._cost_to_dict(r) if r else None

    async def create_cost_allocation(self, data: dict) -> dict:
        self._coerce_uuid_fields(data, ("vehicle_id", "dispatch_id", "related_order_id", "related_install_task_id"))
        r = await self.repo.create_cost_allocation(data)
        await log_operation(
            db=self.db, user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_COST_ALLOCATION, object_id=r.id,
            action=ACTION_CREATE, ip_address=self.ip_address,
            after_data=self._cost_to_dict(r),
        )
        return self._cost_to_dict(r)

    def _cost_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "source_type": r.source_type,
            "source_id": str(r.source_id) if r.source_id else None,
            "vehicle_id": str(r.vehicle_id) if r.vehicle_id else None,
            "vehicle_name": r.vehicle.vehicle_name if r.vehicle else None,
            "plate_number": r.vehicle.plate_number if r.vehicle else None,
            "dispatch_id": str(r.dispatch_id) if r.dispatch_id else None,
            "related_order_id": str(r.related_order_id) if r.related_order_id else None,
            "related_install_task_id": str(r.related_install_task_id) if r.related_install_task_id else None,
            "cost_type": r.cost_type,
            "amount": float(r.amount) if r.amount else 0,
            "allocation_method": r.allocation_method,
            "allocation_date": r.allocation_date.isoformat() if r.allocation_date else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
