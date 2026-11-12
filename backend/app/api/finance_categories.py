from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    PERM_COMPANY_ACCOUNT_LEDGER_READ,
    PERM_EXPENSE_READ,
    PERM_SYSTEM_SUPER_ADMIN,
    require_any_permission,
    require_permission,
)
from app.models.user import User
from app.schemas.common import error, success
from app.schemas.finance_category import FinanceCategoryRename
from app.services.finance_category_service import FinanceCategoryService
from app.services.operation_log_service import ACTION_UPDATE, log_operation


router = APIRouter(prefix="/finance-categories", tags=["Finance Categories"])


@router.get("/")
async def list_finance_categories(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_any_permission(PERM_EXPENSE_READ, PERM_COMPANY_ACCOUNT_LEDGER_READ)),
):
    categories = await FinanceCategoryService(db).list_categories()
    return success([{
        "id": str(category.id),
        "name": category.name,
        "code": category.code,
        "sort_order": category.sort_order,
    } for category in categories])


@router.patch("/{category_id}")
async def rename_finance_category(
    category_id: UUID,
    data: FinanceCategoryRename,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    try:
        result = await FinanceCategoryService(db).rename(category_id, data.name)
    except ValueError as exc:
        return error(40001, str(exc))

    if result["previous_name"] != result["name"]:
        await log_operation(
            db,
            user.id,
            user.real_name or user.username,
            "finance_category",
            category_id,
            ACTION_UPDATE,
            ip_address=request.client.host if request.client else None,
            before_data={"name": result["previous_name"]},
            after_data={
                "name": result["name"],
                "updated_bank_ledger_entries": result["updated_bank_ledger_entries"],
                "updated_project_costs": result["updated_project_costs"],
            },
        )
    return success(result)
