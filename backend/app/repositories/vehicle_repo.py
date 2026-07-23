from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.vehicle import Vehicle, VehicleDriver


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
