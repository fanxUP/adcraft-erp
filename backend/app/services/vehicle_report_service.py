from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vehicle_report_repo import VehicleReportRepository


class VehicleReportService:
    def __init__(self, db: AsyncSession, current_user=None):
        self.db = db
        self.repo = VehicleReportRepository(db)
        self.current_user = current_user

    async def get_overview(self, year: int | None = None, month: int | None = None) -> dict:
        return await self.repo.get_overview(year, month)

    async def get_costs_by_vehicle(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        return await self.repo.get_costs_by_vehicle(year, month, start_date, end_date)

    async def get_costs_by_driver(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        return await self.repo.get_costs_by_driver(year, month, start_date, end_date)

    async def get_mileage_stats(
        self, year: int | None = None, vehicle_id: UUID | None = None,
    ) -> list[dict]:
        return await self.repo.get_mileage_stats(year, vehicle_id)

    async def get_dispatch_stats(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> dict:
        return await self.repo.get_dispatch_stats(year, month, start_date, end_date)

    async def get_order_costs(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        return await self.repo.get_order_costs(year, month, start_date, end_date)

    async def get_cost_by_type(
        self, year: int | None = None, month: int | None = None,
        start_date: str | None = None, end_date: str | None = None,
    ) -> list[dict]:
        return await self.repo.get_cost_by_type(year, month, start_date, end_date)
