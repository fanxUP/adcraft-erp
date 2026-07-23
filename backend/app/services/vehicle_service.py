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


class VehicleService:
    def __init__(self, db: AsyncSession, current_user=None, ip_address: str | None = None):
        self.db = db
        self.repo = VehicleRepository(db)
        self.current_user = current_user
        self.ip_address = ip_address

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

    async def get_vehicle(self, vehicle_id: UUID) -> dict | None:
        v = await self.repo.get_by_id(vehicle_id)
        return self._vehicle_to_dict(v) if v else None

    async def create_vehicle(self, data: dict) -> dict:
        from datetime import datetime
        # 校验车牌号唯一
        existing = await self.repo.get_by_plate(data["plate_number"])
        if existing:
            raise ValueError(f"车牌号 {data['plate_number']} 已存在")
        # 校验车辆编号唯一
        existing_code = await self.repo.get_by_code(data["vehicle_code"])
        if existing_code:
            raise ValueError(f"车辆编号 {data['vehicle_code']} 已存在")

        # 日期字段转换
        for date_field in ["purchase_date"]:
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

        # 如果修改车辆编号，校验唯一
        if "vehicle_code" in data and data["vehicle_code"] and data["vehicle_code"] != v.vehicle_code:
            existing_code = await self.repo.get_by_code(data["vehicle_code"])
            if existing_code:
                raise ValueError(f"车辆编号 {data['vehicle_code']} 已存在")

        # 日期字段转换
        for date_field in ["purchase_date"]:
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
            "vehicle_code": v.vehicle_code,
            "plate_number": v.plate_number,
            "vehicle_name": v.vehicle_name,
            "vehicle_type": v.vehicle_type,
            "brand_model": v.brand_model,
            "color": v.color,
            "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
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

    # ── 用车申请 ──────────────────────────────────────────────────────────────

    async def list_requests(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        requester_id: UUID | None = None,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        requests, total = await self.repo.list_requests(
            skip=skip, limit=page_size, keyword=keyword, status=status, requester_id=requester_id
        )
        return [self._request_to_dict(r) for r in requests], total

    async def get_request(self, request_id: UUID) -> dict | None:
        r = await self.repo.get_request_by_id(request_id)
        return self._request_to_dict(r) if r else None

    async def create_request(self, data: dict) -> dict:
        data.setdefault("requester_id", self.current_user.id if self.current_user else None)
        data.setdefault("status", "draft")
        # 生成申请单号
        from datetime import datetime
        now = datetime.utcnow()
        count = (await self.db.execute(
            select(func.count()).select_from(VehicleUseRequest).where(
                VehicleUseRequest.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        )).scalar() or 0
        data["request_no"] = f"YC{now.strftime('%Y%m%d')}{count + 1:03d}"
        r = await self.repo.create_request(data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_CREATE,
            ip_address=self.ip_address,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    async def update_request(self, request_id: UUID, data: dict) -> dict:
        r = await self.repo.get_request_by_id(request_id)
        if not r:
            raise ValueError("用车申请不存在")
        if r.status not in ("draft", "rejected"):
            raise ValueError("只有草稿或被驳回的申请可以编辑")

        before = self._request_to_dict(r)
        r = await self.repo.update_request(r, data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    async def submit_request(self, request_id: UUID) -> dict:
        r = await self.repo.get_request_by_id(request_id)
        if not r:
            raise ValueError("用车申请不存在")
        if r.status not in ("draft", "rejected"):
            raise ValueError("只有草稿或被驳回的申请可以提交")

        before = self._request_to_dict(r)
        r.status = "pending"
        r.approver_id = None
        r.approved_at = None
        r.reject_reason = None
        await self.db.flush()
        await self.db.refresh(r)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    async def approve_request(self, request_id: UUID) -> dict:
        r = await self.repo.get_request_by_id(request_id)
        if not r:
            raise ValueError("用车申请不存在")
        if r.status != "pending":
            raise ValueError("只有待审批的申请可以审批")

        from datetime import datetime
        before = self._request_to_dict(r)
        r.status = "approved"
        r.approver_id = self.current_user.id if self.current_user else None
        r.approved_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(r)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    async def reject_request(self, request_id: UUID, reject_reason: str) -> dict:
        r = await self.repo.get_request_by_id(request_id)
        if not r:
            raise ValueError("用车申请不存在")
        if r.status != "pending":
            raise ValueError("只有待审批的申请可以驳回")

        from datetime import datetime
        before = self._request_to_dict(r)
        r.status = "rejected"
        r.approver_id = self.current_user.id if self.current_user else None
        r.approved_at = datetime.utcnow()
        r.reject_reason = reject_reason
        await self.db.flush()
        await self.db.refresh(r)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    async def cancel_request(self, request_id: UUID) -> dict:
        r = await self.repo.get_request_by_id(request_id)
        if not r:
            raise ValueError("用车申请不存在")
        if r.status in ("cancelled", "completed", "dispatched"):
            raise ValueError(f"当前状态({r.status})不可取消")

        before = self._request_to_dict(r)
        r.status = "cancelled"
        await self.db.flush()
        await self.db.refresh(r)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_USE_REQUEST,
            object_id=r.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._request_to_dict(r),
        )
        return self._request_to_dict(r)

    def _request_to_dict(self, r) -> dict:
        return {
            "id": str(r.id),
            "request_no": r.request_no,
            "requester_id": str(r.requester_id) if r.requester_id else None,
            "requester_name": r.requester.real_name if r.requester else None,
            "reason": r.reason,
            "related_customer_id": str(r.related_customer_id) if r.related_customer_id else None,
            "customer_name": r.customer.name if r.customer else None,
            "related_order_id": str(r.related_order_id) if r.related_order_id else None,
            "related_install_task_id": str(r.related_install_task_id) if r.related_install_task_id else None,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "expected_return_time": r.expected_return_time.isoformat() if r.expected_return_time else None,
            "destination": r.destination,
            "need_driver": r.need_driver,
            "need_cargo": r.need_cargo,
            "cargo_description": r.cargo_description,
            "estimated_distance_km": float(r.estimated_distance_km) if r.estimated_distance_km else None,
            "status": r.status,
            "approver_id": str(r.approver_id) if r.approver_id else None,
            "approver_name": r.approver.real_name if r.approver else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "reject_reason": r.reject_reason,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    # ── 派车管理 ──────────────────────────────────────────────────────────────

    async def list_dispatches(self, page=1, page_size=20, keyword=None, status=None, vehicle_id=None, driver_id=None):
        skip = (page - 1) * page_size
        return await self.repo.list_dispatches(skip, page_size, keyword, status, vehicle_id, driver_id)

    async def get_dispatch(self, dispatch_id: UUID) -> dict | None:
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            return None
        return self._dispatch_to_dict(d)

    async def create_dispatch(self, data: dict) -> dict:
        # Validate request exists and is approved
        if data.get("request_id"):
            req = await self.repo.get_request_by_id(UUID(data["request_id"]))
            if not req:
                raise ValueError("用车申请不存在")
            if req.status != "approved":
                raise ValueError("只有已审批的申请可以派车")
            # Copy related info from request if not provided
            for field in ("related_customer_id", "related_order_id", "related_install_task_id", "destination"):
                if not data.get(field) and getattr(req, field, None):
                    data[field] = str(getattr(req, field))
            if not data.get("planned_start_time") and req.start_time:
                data["planned_start_time"] = req.start_time.isoformat()
            if not data.get("planned_return_time") and req.expected_return_time:
                data["planned_return_time"] = req.expected_return_time.isoformat()

        # Validate vehicle
        vehicle = await self.repo.get_by_id(UUID(data["vehicle_id"]))
        if not vehicle:
            raise ValueError("车辆不存在")
        if vehicle.status not in ("available",):
            raise ValueError(f"车辆当前状态({vehicle.status})不可派车")

        # Validate driver if provided
        if data.get("driver_id"):
            driver = await self.repo.get_driver_by_id(UUID(data["driver_id"]))
            if not driver:
                raise ValueError("司机不存在")
            if driver.status != "active":
                raise ValueError(f"司机当前状态({driver.status})不可派车")

        # Check time conflict
        from datetime import datetime as dt
        planned_start = data.get("planned_start_time")
        planned_return = data.get("planned_return_time")
        if planned_start and planned_return:
            if isinstance(planned_start, str):
                planned_start = dt.fromisoformat(planned_start)
            if isinstance(planned_return, str):
                planned_return = dt.fromisoformat(planned_return)
            conflict = await self.repo.check_vehicle_conflict(
                UUID(data["vehicle_id"]), planned_start, planned_return
            )
            if conflict:
                raise ValueError("该车辆在指定时间段已有派车安排")

        # Generate dispatch_no
        from datetime import datetime
        now = datetime.utcnow()
        count = (await self.db.execute(
            select(func.count()).select_from(VehicleDispatch).where(
                VehicleDispatch.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
        )).scalar() or 0
        data["dispatch_no"] = f"PC{now.strftime('%Y%m%d')}{count + 1:03d}"
        data["status"] = "assigned"
        data["created_by"] = self.current_user.id if self.current_user else None

        # Convert string IDs
        for field in ("request_id", "vehicle_id", "driver_id", "related_customer_id", "related_order_id", "related_install_task_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])

        d = await self.repo.create_dispatch(data)

        # Update request status to dispatched
        if d.request_id:
            req = await self.repo.get_request_by_id(d.request_id)
            if req:
                req.status = "dispatched"
                await self.db.flush()

        # Update vehicle status to assigned
        vehicle.status = "assigned"
        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_CREATE,
            ip_address=self.ip_address,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    async def update_dispatch(self, dispatch_id: UUID, data: dict) -> dict:
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status not in ("assigned",):
            raise ValueError("只有待出车的派车单可以编辑")

        # Check vehicle conflict if time or vehicle changed
        vehicle_id = UUID(data["vehicle_id"]) if data.get("vehicle_id") else d.vehicle_id
        planned_start = data.get("planned_start_time") or d.planned_start_time
        planned_return = data.get("planned_return_time") or d.planned_return_time
        if planned_start and planned_return:
            if isinstance(planned_start, str):
                from datetime import datetime as dt
                planned_start = dt.fromisoformat(planned_start)
            if isinstance(planned_return, str):
                from datetime import datetime as dt
                planned_return = dt.fromisoformat(planned_return)
            conflict = await self.repo.check_vehicle_conflict(
                vehicle_id, planned_start, planned_return, exclude_id=d.id
            )
            if conflict:
                raise ValueError("该车辆在指定时间段已有派车安排")

        before = self._dispatch_to_dict(d)

        for field in ("vehicle_id", "driver_id", "related_customer_id", "related_order_id", "related_install_task_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])

        d = await self.repo.update_dispatch(d, data)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    async def cancel_dispatch(self, dispatch_id: UUID) -> dict:
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status in ("cancelled", "completed"):
            raise ValueError(f"当前状态({d.status})不可取消")

        before = self._dispatch_to_dict(d)
        d.status = "cancelled"
        await self.db.flush()

        # Restore request status
        if d.request_id:
            req = await self.repo.get_request_by_id(d.request_id)
            if req:
                req.status = "approved"
                await self.db.flush()

        # Restore vehicle status
        vehicle = await self.repo.get_by_id(d.vehicle_id)
        if vehicle and vehicle.status == "assigned":
            vehicle.status = "available"
            await self.db.flush()

        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    # ── 出车/收车操作 ──────────────────────────────────────────────────────────

    async def start_dispatch(self, dispatch_id: UUID, data: dict) -> dict:
        """出车：记录出车时间和里程"""
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status != "assigned":
            raise ValueError("只有待出车状态的派车单可以出车")

        before = self._dispatch_to_dict(d)

        # 更新派车单实际出车时间
        from datetime import datetime as dt
        now = dt.utcnow()
        d.actual_start_time = data.get("start_time") or now
        d.start_mileage = data.get("start_mileage")
        d.status = "started"

        # 创建出车台账
        trip = await self.repo.create_trip_record({
            "dispatch_id": d.id,
            "vehicle_id": d.vehicle_id,
            "driver_id": d.driver_id,
            "trip_date": d.actual_start_time,
            "start_time": d.actual_start_time,
            "start_mileage": data.get("start_mileage"),
            "start_photo_url": data.get("start_photo_url"),
            "start_remark": data.get("start_remark"),
        })
        # 生成台账编号
        trip.trip_no = f"TC{now.strftime('%Y%m%d')}{str(trip.id)[:8]}"

        # 更新车辆状态
        vehicle = await self.repo.get_by_id(d.vehicle_id)
        if vehicle:
            vehicle.status = "in_use"
            await self.db.flush()

        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    async def arrive_dispatch(self, dispatch_id: UUID, data: dict) -> dict:
        """到达现场"""
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status != "started":
            raise ValueError("只有已出车状态可以标记到达")

        before = self._dispatch_to_dict(d)
        from datetime import datetime as dt
        d.status = "arrived"

        # 更新台账
        trip = await self.repo.get_trip_by_dispatch_id(d.id)
        if trip:
            await self.repo.update_trip_record(trip, {
                "return_remark": data.get("arrive_remark"),
            })

        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    async def finish_dispatch(self, dispatch_id: UUID, data: dict) -> dict:
        """完工"""
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status != "arrived":
            raise ValueError("只有已到达状态可以标记完工")

        before = self._dispatch_to_dict(d)
        d.status = "completed"

        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    async def return_dispatch(self, dispatch_id: UUID, data: dict) -> dict:
        """收车：记录收车时间和里程"""
        d = await self.repo.get_dispatch_by_id(dispatch_id)
        if not d:
            raise ValueError("派车单不存在")
        if d.status not in ("completed", "arrived", "started"):
            raise ValueError(f"当前状态({d.status})不可收车")

        before = self._dispatch_to_dict(d)

        from datetime import datetime as dt
        now = dt.utcnow()
        d.actual_return_time = data.get("return_time") or now
        d.end_mileage = data.get("end_mileage")

        # 计算实际公里数
        if d.start_mileage and d.end_mileage:
            if d.end_mileage < d.start_mileage:
                raise ValueError("收车里程不能小于出车里程")
            d.actual_distance_km = round(d.end_mileage - d.start_mileage, 2)

        # 异常处理
        abnormal = data.get("abnormal_flag", False)
        d.abnormal_flag = abnormal
        d.abnormal_description = data.get("abnormal_description")
        d.status = "returned"

        # 更新台账
        trip = await self.repo.get_trip_by_dispatch_id(d.id)
        if trip:
            update_data = {
                "return_time": d.actual_return_time,
                "end_mileage": data.get("end_mileage"),
                "distance_km": d.actual_distance_km,
                "return_photo_url": data.get("return_photo_url"),
                "return_remark": data.get("return_remark"),
                "abnormal_flag": abnormal,
                "abnormal_description": data.get("abnormal_description"),
            }
            await self.repo.update_trip_record(trip, update_data)

        # 更新车辆状态
        vehicle = await self.repo.get_by_id(d.vehicle_id)
        if vehicle:
            if abnormal:
                vehicle.status = "maintenance"
            else:
                vehicle.status = "available"

        await self.db.flush()
        await self.db.refresh(d)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_DISPATCH,
            object_id=d.id,
            action=ACTION_STATUS_CHANGE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._dispatch_to_dict(d),
        )
        return self._dispatch_to_dict(d)

    # ── 出车/收车台账 ──────────────────────────────────────────────────────────

    async def list_trip_records(self, page=1, page_size=20, vehicle_id=None, driver_id=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_trip_records(skip, page_size, vehicle_id, driver_id)
        return [self._trip_to_dict(r) for r in records], total

    async def get_trip_record(self, trip_id: UUID) -> dict | None:
        r = await self.repo.get_trip_record_by_id(trip_id)
        return self._trip_to_dict(r) if r else None

    def _trip_to_dict(self, t) -> dict:
        return {
            "id": str(t.id),
            "trip_no": t.trip_no,
            "dispatch_id": str(t.dispatch_id) if t.dispatch_id else None,
            "dispatch_no": t.dispatch.dispatch_no if t.dispatch else None,
            "vehicle_id": str(t.vehicle_id) if t.vehicle_id else None,
            "vehicle_name": t.vehicle.vehicle_name if t.vehicle else None,
            "plate_number": t.vehicle.plate_number if t.vehicle else None,
            "driver_id": str(t.driver_id) if t.driver_id else None,
            "driver_name": t.driver.driver_name if t.driver else None,
            "trip_date": t.trip_date.isoformat() if t.trip_date else None,
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "return_time": t.return_time.isoformat() if t.return_time else None,
            "start_mileage": float(t.start_mileage) if t.start_mileage else None,
            "end_mileage": float(t.end_mileage) if t.end_mileage else None,
            "distance_km": float(t.distance_km) if t.distance_km else None,
            "start_photo_url": t.start_photo_url,
            "return_photo_url": t.return_photo_url,
            "start_remark": t.start_remark,
            "return_remark": t.return_remark,
            "abnormal_flag": t.abnormal_flag,
            "abnormal_description": t.abnormal_description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    def _dispatch_to_dict(self, d) -> dict:
        return {
            "id": str(d.id),
            "dispatch_no": d.dispatch_no,
            "request_id": str(d.request_id) if d.request_id else None,
            "request_no": d.request.request_no if d.request else None,
            "vehicle_id": str(d.vehicle_id) if d.vehicle_id else None,
            "vehicle_name": d.vehicle.vehicle_name if d.vehicle else None,
            "plate_number": d.vehicle.plate_number if d.vehicle else None,
            "driver_id": str(d.driver_id) if d.driver_id else None,
            "driver_name": d.driver.driver_name if d.driver else None,
            "companions": d.companions,
            "related_customer_id": str(d.related_customer_id) if d.related_customer_id else None,
            "related_order_id": str(d.related_order_id) if d.related_order_id else None,
            "related_install_task_id": str(d.related_install_task_id) if d.related_install_task_id else None,
            "start_location": d.start_location,
            "destination": d.destination,
            "planned_start_time": d.planned_start_time.isoformat() if d.planned_start_time else None,
            "planned_return_time": d.planned_return_time.isoformat() if d.planned_return_time else None,
            "actual_start_time": d.actual_start_time.isoformat() if d.actual_start_time else None,
            "actual_return_time": d.actual_return_time.isoformat() if d.actual_return_time else None,
            "status": d.status,
            "remark": d.remark,
            "created_by": str(d.created_by) if d.created_by else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }

    # ── 油费记录 ──────────────────────────────────────────────────────────────────

    async def list_fuel_records(self, page=1, page_size=20, vehicle_id=None, driver_id=None, status=None):
        skip = (page - 1) * page_size
        records, total = await self.repo.list_fuel_records(skip, page_size, vehicle_id, driver_id, status)
        return [self._fuel_to_dict(r) for r in records], total

    async def get_fuel_record(self, record_id: UUID) -> dict | None:
        r = await self.repo.get_fuel_record_by_id(record_id)
        return self._fuel_to_dict(r) if r else None

    async def create_fuel_record(self, data: dict) -> dict:
        for field in ("vehicle_id", "driver_id", "dispatch_id", "payer_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        r = await self.repo.get_fuel_record_by_id(record_id)
        if not r:
            raise ValueError("油费记录不存在")
        if r.status not in ("pending_review", "rejected"):
            raise ValueError("只有待审核或已驳回的记录可以编辑")
        before = self._fuel_to_dict(r)
        for field in ("vehicle_id", "driver_id", "dispatch_id", "payer_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        for field in ("vehicle_id", "handler_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        r = await self.repo.get_maintenance_record_by_id(record_id)
        if not r:
            raise ValueError("维修保养记录不存在")
        if r.status not in ("pending_review", "rejected"):
            raise ValueError("只有待审核或已驳回的记录可以编辑")
        before = self._maintenance_to_dict(r)
        for field in ("vehicle_id", "handler_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        for field in ("vehicle_id", "dispatch_id", "related_order_id", "related_install_task_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        for field in ("vehicle_id", "driver_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        r = await self.repo.get_certificate_by_id(cert_id)
        if not r:
            raise ValueError("证件记录不存在")
        before = self._certificate_to_dict(r)
        for field in ("vehicle_id", "driver_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        for field in ("vehicle_id", "driver_id", "dispatch_id", "related_order_id", "related_install_task_id", "responsible_user_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
        r = await self.repo.get_incident_by_id(incident_id)
        if not r:
            raise ValueError("异常记录不存在")
        before = self._incident_to_dict(r)
        for field in ("vehicle_id", "driver_id", "dispatch_id", "related_order_id", "related_install_task_id", "responsible_user_id"):
            if data.get(field) and isinstance(data[field], str):
                data[field] = UUID(data[field])
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
