import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.schemas.common import success
from app.services.department_service import DepartmentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/")
async def list_departments(keyword: str | None = None, include_inactive: bool = Query(False), db=Depends(get_db), current_user=Depends(get_current_user)):
    return success(await DepartmentService(db).list_departments(keyword, include_inactive=include_inactive))


@router.post("/")
async def create_department(data: DepartmentCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await DepartmentService(db).create_department(data.model_dump()))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.get("/{department_id}")
async def get_department(department_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    d = await DepartmentService(db).get_department(UUID(department_id))
    if not d:
        return {"code": 40401, "message": "部门不存在", "data": None}
    return success(d)


@router.put("/{department_id}")
async def update_department(department_id: str, data: DepartmentUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return success(await DepartmentService(db).update_department(UUID(department_id), data.model_dump(exclude_none=True)))
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.delete("/{department_id}")
async def delete_department(department_id: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        if not await DepartmentService(db).delete_department(UUID(department_id)):
            return {"code": 40401, "message": "部门不存在", "data": None}
        return success(None)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}
