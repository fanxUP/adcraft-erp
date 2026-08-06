import os
import uuid
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

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


class VehicleRegistryService(VehicleServiceBase):
    # ── 车辆档案 ──────────────────────────────────────────────────────────────

    async def list_vehicles(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        vehicle_type: str | None = None,
        status: str | None = None,
        driver_id: UUID | None = None,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        vehicles, total = await self.repo.list_vehicles(
            skip=skip, limit=page_size,
            keyword=keyword, vehicle_type=vehicle_type,
            status=status, driver_id=driver_id,
        )
        return [self._vehicle_to_dict(v) for v in vehicles], total

    async def list_vehicles_expiring(self, days: int = 30) -> list[dict]:
        """保险/年检在 N 天内到期或已过期的车辆，附 days_left 与 urgency。"""
        from datetime import datetime
        vehicles = await self.repo.list_expiring_vehicles(days)
        now = datetime.now().date()
        result = []
        for v in vehicles:
            item = {
                "vehicle_id": str(v.id),
                "plate_number": v.plate_number,
                "vehicle_name": v.vehicle_name,
                "insurance_expire_date": None,
                "insurance_days_left": None,
                "insurance_urgency": None,
                "inspection_expire_date": None,
                "inspection_days_left": None,
                "inspection_urgency": None,
            }
            for field in ("insurance", "inspection"):
                d = getattr(v, f"{field}_expire_date")
                if d:
                    days_left = (d.date() - now).days
                    if days_left <= days:
                        if days_left < 0:
                            urgency = "expired"
                        elif days_left <= 7:
                            urgency = "urgent"
                        else:
                            urgency = "warning"
                        item[f"{field}_expire_date"] = d.isoformat()[:10]
                        item[f"{field}_days_left"] = days_left
                        item[f"{field}_urgency"] = urgency
            result.append(item)
        return result

    async def get_vehicle(self, vehicle_id: UUID) -> dict | None:
        v = await self.repo.get_by_id(vehicle_id)
        return self._vehicle_to_dict(v) if v else None

    async def create_vehicle(self, data: dict) -> dict:
        from datetime import datetime
        # 校验车牌号唯一
        existing = await self.repo.get_by_plate(data["plate_number"])
        if existing:
            raise ValueError(f"车牌号 {data['plate_number']} 已存在")

        # 日期字段转换
        for date_field in ["purchase_date", "insurance_expire_date", "inspection_expire_date", "maintenance_due_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None

        data.setdefault("status", "available")
        v = await self.repo.create_vehicle(data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE,
            object_id=v.id,
            action=ACTION_CREATE,
            ip_address=self.ip_address,
            after_data=self._vehicle_to_dict(v),
        )
        return self._vehicle_to_dict(v)

    async def update_vehicle(self, vehicle_id: UUID, data: dict) -> dict:
        from datetime import datetime
        v = await self.repo.get_by_id(vehicle_id)
        if not v:
            raise ValueError("车辆不存在")

        before = self._vehicle_to_dict(v)

        # 如果修改车牌号，校验唯一
        if "plate_number" in data and data["plate_number"] and data["plate_number"] != v.plate_number:
            existing = await self.repo.get_by_plate(data["plate_number"])
            if existing:
                raise ValueError(f"车牌号 {data['plate_number']} 已存在")

        # 日期字段转换
        for date_field in ["purchase_date", "insurance_expire_date", "inspection_expire_date", "maintenance_due_date"]:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None

        v = await self.repo.update_vehicle(v, data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE,
            object_id=v.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._vehicle_to_dict(v),
        )
        return self._vehicle_to_dict(v)

    async def delete_vehicle(self, vehicle_id: UUID) -> dict:
        v = await self.repo.get_by_id(vehicle_id)
        if not v:
            raise ValueError("车辆不存在")
        before = self._vehicle_to_dict(v)
        await self.repo.soft_delete_vehicle(v)
        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE,
            object_id=v.id,
            action=ACTION_DELETE,
            ip_address=self.ip_address,
            before_data=before,
        )
        return before

    async def disable_vehicle(self, vehicle_id: UUID) -> dict:
        return await self._change_status(vehicle_id, "disabled", "停用")

    async def enable_vehicle(self, vehicle_id: UUID) -> dict:
        return await self._change_status(vehicle_id, "available", "启用")

    async def scrap_vehicle(self, vehicle_id: UUID) -> dict:
        return await self._change_status(vehicle_id, "scrapped", "报废")

    async def _change_status(self, vehicle_id: UUID, new_status: str, action_label: str) -> dict:
        v = await self.repo.get_by_id(vehicle_id)
        if not v:
            raise ValueError("车辆不存在")

        before = self._vehicle_to_dict(v)
        old_status = v.status

        # 状态合法性校验
        if new_status == "available" and old_status not in ("disabled",):
            raise ValueError("只有停用状态的车辆才能启用")
        if new_status == "disabled" and old_status in ("scrapped",):
            raise ValueError("已报废车辆不能停用")
        if new_status == "scrapped" and old_status in ("scrapped",):
            raise ValueError("车辆已报废")

        v.status = new_status
        await self.db.flush()
        await self.db.refresh(v)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE,
            object_id=v.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._vehicle_to_dict(v),
        )
        return self._vehicle_to_dict(v)

    def _vehicle_to_dict(self, v) -> dict:
        return {
            "id": str(v.id),
            "plate_number": v.plate_number,
            "vehicle_name": v.vehicle_name,
            "vehicle_type": v.vehicle_type,
            "brand_model": v.brand_model,
            "color": v.color,
            "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
            "insurance_expire_date": v.insurance_expire_date.isoformat() if v.insurance_expire_date else None,
            "inspection_expire_date": v.inspection_expire_date.isoformat() if v.inspection_expire_date else None,
            "maintenance_due_date": v.maintenance_due_date.isoformat() if v.maintenance_due_date else None,
            "status": v.status,
            "department": v.department,
            "default_driver_id": str(v.default_driver_id) if v.default_driver_id else None,
            "default_driver_name": v.default_driver.driver_name if v.default_driver else None,
            "load_capacity": v.load_capacity,
            "seats": v.seats,
            "vehicle_photo_url": v.vehicle_photo_url,
            "license_photo_url": v.license_photo_url,
            "remark": v.remark,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }

    # ── 司机档案 ──────────────────────────────────────────────────────────────

    async def list_drivers(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        drivers, total = await self.repo.list_drivers(skip=skip, limit=page_size, keyword=keyword, status=status)
        return [self._driver_to_dict(d) for d in drivers], total

    async def get_driver(self, driver_id: UUID) -> dict | None:
        d = await self.repo.get_driver_by_id(driver_id)
        return self._driver_to_dict(d) if d else None

    async def create_driver(self, data: dict) -> dict:
        from datetime import datetime
        data.setdefault("status", "active")
        # 日期字段转换
        if "license_expire_date" in data and isinstance(data["license_expire_date"], str):
            try:
                data["license_expire_date"] = datetime.fromisoformat(data["license_expire_date"])
            except ValueError:
                data["license_expire_date"] = None
        d = await self.repo.create_driver(data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DRIVER,
            object_id=d.id,
            action=ACTION_CREATE,
            ip_address=self.ip_address,
            after_data=self._driver_to_dict(d),
        )
        return self._driver_to_dict(d)

    async def update_driver(self, driver_id: UUID, data: dict) -> dict:
        from datetime import datetime
        d = await self.repo.get_driver_by_id(driver_id)
        if not d:
            raise ValueError("司机不存在")

        # 日期字段转换
        if "license_expire_date" in data and isinstance(data["license_expire_date"], str):
            try:
                data["license_expire_date"] = datetime.fromisoformat(data["license_expire_date"])
            except ValueError:
                data["license_expire_date"] = None

        before = self._driver_to_dict(d)
        d = await self.repo.update_driver(d, data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DRIVER,
            object_id=d.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._driver_to_dict(d),
        )
        return self._driver_to_dict(d)

    async def delete_driver(self, driver_id: UUID) -> dict:
        d = await self.repo.get_driver_by_id(driver_id)
        if not d:
            raise ValueError("司机不存在")
        before = self._driver_to_dict(d)
        await self.repo.soft_delete_driver(d)
        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DRIVER,
            object_id=d.id,
            action=ACTION_DELETE,
            ip_address=self.ip_address,
            before_data=before,
        )
        return before

    async def disable_driver(self, driver_id: UUID) -> dict:
        return await self._change_driver_status(driver_id, "disabled", "停用")

    async def enable_driver(self, driver_id: UUID) -> dict:
        return await self._change_driver_status(driver_id, "active", "启用")

    async def _change_driver_status(self, driver_id: UUID, new_status: str, action_label: str) -> dict:
        d = await self.repo.get_driver_by_id(driver_id)
        if not d:
            raise ValueError("司机不存在")

        before = self._driver_to_dict(d)
        d.status = new_status
        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DRIVER,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._driver_to_dict(d),
        )
        return self._driver_to_dict(d)

    def _driver_to_dict(self, d) -> dict:
        return {
            "id": str(d.id),
            "employee_id": str(d.employee_id) if d.employee_id else None,
            "employee_name": d.employee.real_name if d.employee else None,
            "driver_name": d.driver_name,
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

    # ── 车辆附件 ─────────────────────────────────────────────────────────────

    async def save_upload_file(self, file):
        """把上传文件落盘到 {LOCAL_UPLOAD_DIR}/{YYYYMM}/uuid.ext，返回 /uploads/ 相对路径。"""
        from datetime import datetime
        upload_dir = settings.LOCAL_UPLOAD_DIR
        date_dir = datetime.now().strftime("%Y%m")
        dest_dir = os.path.join(upload_dir, date_dir)
        os.makedirs(dest_dir, exist_ok=True)
        ext = file.filename.rsplit(".", 1)[1] if file.filename and "." in file.filename else ""
        fn = f"{uuid.uuid4().hex}.{ext}"
        fp = os.path.join(dest_dir, fn)
        content = await file.read()
        with open(fp, "wb") as f:
            f.write(content)
        return {
            "file_url": f"/uploads/{date_dir}/{fn}",
            "file_name": file.filename or fn,
            "file_size": len(content),
        }

    async def list_vehicle_attachments(self, vehicle_id: UUID, attachment_type: str | None = None) -> list[dict]:
        items = await self.repo.list_vehicle_attachments(vehicle_id, attachment_type)
        return [self._vehicle_attachment_to_dict(a) for a in items]

    async def create_vehicle_attachment(self, vehicle_id: str, file, attachment_type: str = "other", remark: str = "") -> dict:
        v = await self.repo.get_by_id(uuid.UUID(vehicle_id))
        if not v:
            raise ValueError("车辆不存在")
        saved = await self.save_upload_file(file)
        data = {
            "vehicle_id": uuid.UUID(vehicle_id),
            "attachment_type": attachment_type or "other",
            "file_url": saved["file_url"],
            "file_name": saved["file_name"],
            "remark": remark or None,
            "uploaded_by": self.current_user.id if self.current_user else None,
        }
        att = await self.repo.create_vehicle_attachment(data)
        return self._vehicle_attachment_to_dict(att)

    async def delete_vehicle_attachment(self, attachment_id: str) -> dict:
        obj = await self.repo.delete_vehicle_attachment(uuid.UUID(attachment_id))
        if not obj:
            raise ValueError("附件不存在")
        return {"id": attachment_id, "deleted": True}

    def _vehicle_attachment_to_dict(self, a) -> dict:
        return {
            "id": str(a.id),
            "vehicle_id": str(a.vehicle_id),
            "attachment_type": a.attachment_type,
            "file_url": a.file_url,
            "file_name": a.file_name,
            "uploaded_by": str(a.uploaded_by) if a.uploaded_by else None,
            "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
            "remark": a.remark,
        }
