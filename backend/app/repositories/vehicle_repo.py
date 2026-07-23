from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.vehicle import Vehicle, VehicleDriver, VehicleUseRequest, VehicleDispatch, VehicleTripRecord


class VehicleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 车辆档案 ──────────────────────────────────────────────────────────────

    async def get_by_id(self, vehicle_id: UUID) -> Vehicle | None:
        result = await self.db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
        return result.scalar_one_or_none()

    async def get_by_plate(self, plate_number: str) -> Vehicle | None:
        result = await self.db.execute(select(Vehicle).where(Vehicle.plate_number == plate_number))
        return result.scalar_one_or_none()

    async def get_by_code(self, vehicle_code: str) -> Vehicle | None:
        result = await self.db.execute(select(Vehicle).where(Vehicle.vehicle_code == vehicle_code))
        return result.scalar_one_or_none()

    async def list_vehicles(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        vehicle_type: str | None = None,
        status: str | None = None,
        driver_id: UUID | None = None,
    ) -> tuple[list[Vehicle], int]:
        q = select(Vehicle)
        if keyword:
            q = q.where(
                Vehicle.plate_number.ilike(f"%{keyword}%")
                | Vehicle.vehicle_name.ilike(f"%{keyword}%")
                | Vehicle.vehicle_code.ilike(f"%{keyword}%")
            )
        if vehicle_type:
            q = q.where(Vehicle.vehicle_type == vehicle_type)
        if status:
            q = q.where(Vehicle.status == status)
        if driver_id:
            q = q.where(Vehicle.default_driver_id == driver_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(Vehicle.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_vehicle(self, data: dict) -> Vehicle:
        vehicle = Vehicle(**data)
        self.db.add(vehicle)
        await self.db.flush()
        await self.db.refresh(vehicle)
        return vehicle

    async def update_vehicle(self, vehicle: Vehicle, data: dict) -> Vehicle:
        for k, v in data.items():
            if v is not None:
                setattr(vehicle, k, v)
        await self.db.flush()
        await self.db.refresh(vehicle)
        return vehicle

    # ── 司机档案 ──────────────────────────────────────────────────────────────

    async def get_driver_by_id(self, driver_id: UUID) -> VehicleDriver | None:
        result = await self.db.execute(select(VehicleDriver).where(VehicleDriver.id == driver_id))
        return result.scalar_one_or_none()

    async def list_drivers(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[VehicleDriver], int]:
        q = select(VehicleDriver)
        if keyword:
            q = q.where(
                VehicleDriver.driver_name.ilike(f"%{keyword}%")
                | VehicleDriver.phone.ilike(f"%{keyword}%")
            )
        if status:
            q = q.where(VehicleDriver.status == status)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(VehicleDriver.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_driver(self, data: dict) -> VehicleDriver:
        driver = VehicleDriver(**data)
        self.db.add(driver)
        await self.db.flush()
        await self.db.refresh(driver)
        return driver

    async def update_driver(self, driver: VehicleDriver, data: dict) -> VehicleDriver:
        for k, v in data.items():
            if v is not None:
                setattr(driver, k, v)
        await self.db.flush()
        await self.db.refresh(driver)
        return driver

    # ── 用车申请 ──────────────────────────────────────────────────────────────

    async def get_request_by_id(self, request_id: UUID) -> VehicleUseRequest | None:
        result = await self.db.execute(select(VehicleUseRequest).where(VehicleUseRequest.id == request_id))
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        requester_id: UUID | None = None,
    ) -> tuple[list[VehicleUseRequest], int]:
        q = select(VehicleUseRequest)
        if keyword:
            q = q.where(
                VehicleUseRequest.reason.ilike(f"%{keyword}%")
                | VehicleUseRequest.destination.ilike(f"%{keyword}%")
            )
        if status:
            q = q.where(VehicleUseRequest.status == status)
        if requester_id:
            q = q.where(VehicleUseRequest.requester_id == requester_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(VehicleUseRequest.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_request(self, data: dict) -> VehicleUseRequest:
        req = VehicleUseRequest(**data)
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)
        return req

    async def update_request(self, req: VehicleUseRequest, data: dict) -> VehicleUseRequest:
        for k, v in data.items():
            if v is not None:
                setattr(req, k, v)
        await self.db.flush()
        await self.db.refresh(req)
        return req

    # ── 派车单 ──────────────────────────────────────────────────────────────────

    async def get_dispatch_by_id(self, dispatch_id: UUID) -> VehicleDispatch | None:
        result = await self.db.execute(select(VehicleDispatch).where(VehicleDispatch.id == dispatch_id))
        return result.scalar_one_or_none()

    async def list_dispatches(
        self,
        skip: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        vehicle_id: UUID | None = None,
        driver_id: UUID | None = None,
    ) -> tuple[list[VehicleDispatch], int]:
        q = select(VehicleDispatch)
        if keyword:
            q = q.where(
                VehicleDispatch.dispatch_no.ilike(f"%{keyword}%")
                | VehicleDispatch.destination.ilike(f"%{keyword}%")
            )
        if status:
            q = q.where(VehicleDispatch.status == status)
        if vehicle_id:
            q = q.where(VehicleDispatch.vehicle_id == vehicle_id)
        if driver_id:
            q = q.where(VehicleDispatch.driver_id == driver_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(VehicleDispatch.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_dispatch(self, data: dict) -> VehicleDispatch:
        d = VehicleDispatch(**data)
        self.db.add(d)
        await self.db.flush()
        await self.db.refresh(d)
        return d

    async def update_dispatch(self, d: VehicleDispatch, data: dict) -> VehicleDispatch:
        for k, v in data.items():
            if v is not None:
                setattr(d, k, v)
        await self.db.flush()
        await self.db.refresh(d)
        return d

    async def check_vehicle_conflict(
        self,
        vehicle_id: UUID,
        planned_start: datetime,
        planned_return: datetime,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if vehicle has time conflict with existing dispatches."""
        q = select(VehicleDispatch).where(
            VehicleDispatch.vehicle_id == vehicle_id,
            VehicleDispatch.status.notin_(["cancelled"]),
            VehicleDispatch.planned_start_time.isnot(None),
            VehicleDispatch.planned_return_time.isnot(None),
            VehicleDispatch.planned_start_time < planned_return,
            VehicleDispatch.planned_return_time > planned_start,
        )
        if exclude_id:
            q = q.where(VehicleDispatch.id != exclude_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none() is not None

    # ── 出车/收车台账 ──────────────────────────────────────────────────────────

    async def get_trip_record_by_id(self, trip_id: UUID) -> VehicleTripRecord | None:
        result = await self.db.execute(select(VehicleTripRecord).where(VehicleTripRecord.id == trip_id))
        return result.scalar_one_or_none()

    async def get_trip_by_dispatch_id(self, dispatch_id: UUID) -> VehicleTripRecord | None:
        result = await self.db.execute(select(VehicleTripRecord).where(VehicleTripRecord.dispatch_id == dispatch_id))
        return result.scalar_one_or_none()

    async def list_trip_records(
        self,
        skip: int = 0,
        limit: int = 20,
        vehicle_id: UUID | None = None,
        driver_id: UUID | None = None,
    ) -> tuple[list[VehicleTripRecord], int]:
        q = select(VehicleTripRecord)
        if vehicle_id:
            q = q.where(VehicleTripRecord.vehicle_id == vehicle_id)
        if driver_id:
            q = q.where(VehicleTripRecord.driver_id == driver_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(VehicleTripRecord.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_trip_record(self, data: dict) -> VehicleTripRecord:
        t = VehicleTripRecord(**data)
        self.db.add(t)
        await self.db.flush()
        await self.db.refresh(t)
        return t

    async def update_trip_record(self, t: VehicleTripRecord, data: dict) -> VehicleTripRecord:
        for k, v in data.items():
            if v is not None:
                setattr(t, k, v)
        await self.db.flush()
        await self.db.refresh(t)
        return t
