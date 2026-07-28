from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vehicle_repo import VehicleRepository


class VehicleServiceBase:
    """车辆领域服务共享运行上下文。"""

    def __init__(
        self,
        db: AsyncSession,
        current_user=None,
        ip_address: str | None = None,
    ):
        self.db = db
        self.repo = VehicleRepository(db)
        self.current_user = current_user
        self.ip_address = ip_address
