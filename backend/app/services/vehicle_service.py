from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import VehicleUseRequest
from app.repositories.vehicle_repo import VehicleRepository
from app.services.operation_log_service import (
    log_operation, OBJ_VEHICLE, OBJ_VEHICLE_DRIVER, OBJ_VEHICLE_USE_REQUEST,
    ACTION_CREATE, ACTION_UPDATE, ACTION_STATUS_CHANGE,
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
        # 校验车牌号唯一
        existing = await self.repo.get_by_plate(data["plate_number"])
        if existing:
            raise ValueError(f"车牌号 {data['plate_number']} 已存在")
        # 校验车辆编号唯一
        existing_code = await self.repo.get_by_code(data["vehicle_code"])
        if existing_code:
            raise ValueError(f"车辆编号 {data['vehicle_code']} 已存在")

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
        data.setdefault("status", "active")
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
        d = await self.repo.get_driver_by_id(driver_id)
        if not d:
            raise ValueError("司机不存在")

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
