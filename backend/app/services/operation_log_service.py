from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.operation_log_repo import OperationLogRepository


# Object types for consistent logging
OBJ_CUSTOMER = "customer"
OBJ_QUOTE = "quote"
OBJ_ORDER = "order"
OBJ_PAYMENT = "payment"
OBJ_EXPENSE = "expense"
OBJ_OUTSOURCE_VENDOR = "outsource_vendor"
OBJ_OUTSOURCE_TASK = "outsource_task"
OBJ_OUTSOURCE_PAYMENT = "outsource_payment"
OBJ_INVENTORY = "inventory"
OBJ_PRODUCTION_TASK = "production_task"
OBJ_DESIGN_TASK = "design_task"
OBJ_INSTALLATION_TASK = "installation_task"
OBJ_PROJECT_COST = "project_cost"
OBJ_CONTRACT = "contract"
OBJ_VEHICLE = "vehicle"
OBJ_VEHICLE_DRIVER = "vehicle_driver"
OBJ_VEHICLE_USE_REQUEST = "vehicle_use_request"

# Actions
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_STATUS_CHANGE = "status_change"
ACTION_STOCK_IN = "stock_in"
ACTION_STOCK_OUT = "stock_out"
ACTION_CONFIRM = "confirm"
ACTION_CONVERT = "convert"  # quote -> order


async def log_operation(
    db: AsyncSession,
    user_id: UUID | None,
    user_name: str | None,
    object_type: str,
    object_id: UUID | None,
    action: str,
    ip_address: str | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
) -> None:
    """Utility function to log an operation. Can be called from any service."""
    repo = OperationLogRepository(db)
    await repo.create({
        "user_id": user_id,
        "user_name": user_name,
        "object_type": object_type,
        "object_id": object_id,
        "action": action,
        "ip_address": ip_address,
        "before_data": before_data,
        "after_data": after_data,
    })


class OperationLogService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OperationLogRepository(db)

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: UUID | None = None,
        object_type: str | None = None,
        action: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        logs, total = await self.repo.list_logs(
            skip=skip, limit=page_size,
            user_id=user_id, object_type=object_type,
            action=action, date_from=date_from, date_to=date_to,
        )
        return [self._log_to_dict(log) for log in logs], total

    async def get_log(self, log_id: UUID) -> dict | None:
        log = await self.repo.get_by_id(log_id)
        if not log:
            return None
        return self._log_to_dict(log)

    def _log_to_dict(self, log) -> dict:
        return {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": log.user_name,
            "object_type": log.object_type,
            "object_id": str(log.object_id) if log.object_id else None,
            "action": log.action,
            "before_data": log.before_data,
            "after_data": log.after_data,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
