from uuid import UUID

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

    @staticmethod
    def _coerce_uuid_fields(data: dict, fields: tuple[str, ...]) -> None:
        """把可选 UUID 字符串字段转为 UUID；空串/纯空白视为 None，避免 asyncpg invalid UUID '' 报错。"""
        for field in fields:
            val = data.get(field)
            if isinstance(val, str):
                data[field] = None if not val.strip() else UUID(val)
