import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.employee_repo import EmployeeRepository
from app.services.number_generator import generate_employee_no
from app.models.employee import Employee
from app.models.user import User

logger = logging.getLogger(__name__)

def _convert_license_expire_date(data: dict) -> dict:
    """license_expire_date: 空串/None -> None，ISO 字符串 -> datetime（列是 DateTime）。"""
    if "license_expire_date" in data:
        raw = data.get("license_expire_date")
        data["license_expire_date"] = datetime.fromisoformat(raw) if raw else None
    return data

class EmployeeService:
    def __init__(self, db: AsyncSession): self.db = db; self.repo = EmployeeRepository(db)
    async def list_employees(self, page=1, page_size=20, keyword=None, dept=None, status=None):
        skip = (page-1)*page_size
        emps, total = await self.repo.list(skip, page_size, keyword, dept, status)
        return [self._d(e) for e in emps], total
    async def get_employee(self, eid): e = await self.repo.get_by_id(eid); return self._d(e) if e else None
    async def create_employee(self, data):
        raw_user_id = data.get("user_id")
        binding_user = None
        if raw_user_id not in (None, ""):
            binding_user_id = self._coerce_user_id(raw_user_id)
            if data.get("employment_status", "active") != "active" or data.get("is_active", True) is not True:
                raise ValueError("只有在职且启用的员工档案可以绑定登录账号")
            binding_user = await self._load_bindable_user(binding_user_id)
            await self._ensure_user_not_bound(binding_user_id)
            data["user_id"] = binding_user_id
        else:
            data["user_id"] = None
        if not data.get("employee_no"):
            data["employee_no"] = await generate_employee_no(self.db)
        _convert_license_expire_date(data)
        employee = await self.repo.create(data)
        result = self._d(employee)
        if binding_user is not None:
            result.update({
                "user_username": binding_user.username,
                "user_real_name": binding_user.real_name,
            })
        return result
    async def update_employee(self, eid, data):
        e = await self.repo.get_by_id(eid)
        if not e: raise ValueError("员工不存在")
        if "user_id" in data:
            raise ValueError("请在“登录账号”绑定操作中修改账号关系")
        _convert_license_expire_date(data)
        return self._d(await self.repo.update(e, data))

    @staticmethod
    def _coerce_user_id(raw_user_id) -> UUID:
        if isinstance(raw_user_id, UUID):
            return raw_user_id
        try:
            return UUID(str(raw_user_id))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("登录账号编号格式不正确，请重新选择") from exc

    async def _load_bindable_user(self, user_id: UUID):
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("登录账号不存在或已停用，请重新选择")
        return user

    async def _ensure_user_not_bound(self, user_id: UUID, employee_id: UUID | None = None):
        conditions = [
            Employee.user_id == user_id,
            Employee.deleted_at.is_(None),
        ]
        if employee_id is not None:
            conditions.append(Employee.id != employee_id)
        result = await self.db.execute(select(Employee).where(*conditions))
        employee = result.scalar_one_or_none()
        if employee is not None:
            raise ValueError(
                f"该登录账号已绑定员工“{employee.employee_no} {employee.name}”，请先解除原绑定"
            )

    async def list_account_options(self, employee_id: UUID | None = None):
        conditions = [
            Employee.user_id == User.id,
            Employee.deleted_at.is_(None),
        ]
        if employee_id is not None:
            conditions.append(Employee.id != employee_id)
        bound_to_other = exists(select(Employee.id).where(*conditions))
        result = await self.db.execute(
            select(User)
            .where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                ~bound_to_other,
            )
            .order_by(User.real_name.asc().nullslast(), User.username.asc())
        )
        return [
            {
                "id": str(user.id),
                "username": user.username,
                "real_name": user.real_name,
            }
            for user in result.scalars().all()
        ]

    async def bind_user(self, employee_id: UUID, raw_user_id):
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            raise ValueError("员工不存在")

        if raw_user_id in (None, ""):
            employee.user_id = None
            await self.db.flush()
            return self._d(employee)

        if employee.employment_status != "active" or employee.is_active is not True:
            raise ValueError("只有在职且启用的员工档案可以绑定登录账号")
        user_id = self._coerce_user_id(raw_user_id)
        user = await self._load_bindable_user(user_id)
        await self._ensure_user_not_bound(user_id, employee_id)
        employee.user_id = user_id
        await self.db.flush()
        result = self._d(employee)
        result.update({"user_username": user.username, "user_real_name": user.real_name})
        return result
    async def delete_employee(self, eid):
        e = await self.repo.get_by_id(eid)
        if not e: return False
        await self.repo.soft_delete(e); return True
    def _d(self, e):
        linked_user = getattr(e, "user", None)
        if not isinstance(linked_user, User):
            linked_user = None
        return {"id": str(e.id), "employee_no": e.employee_no, "name": e.name, "phone": e.phone,
            "gender": e.gender, "ethnicity": e.ethnicity,
            "birth_date": e.birth_date.isoformat() if e.birth_date else None,
            "department": e.department, "position": e.position,
            "employment_type": e.employment_type, "employment_status": e.employment_status,
            "hire_date": e.hire_date.isoformat() if e.hire_date else None,
            "resignation_date": e.resignation_date.isoformat() if e.resignation_date else None,
            "id_card": e.id_card, "education": e.education,
            "license_no": e.license_no, "license_type": e.license_type,
            "license_expire_date": e.license_expire_date.isoformat() if e.license_expire_date else None,
            "id_card_front_url": e.id_card_front_url, "id_card_back_url": e.id_card_back_url,
            "emergency_contact": e.emergency_contact, "emergency_phone": e.emergency_phone,
            "skills": e.skills if isinstance(e.skills, list) else [],
            "bank_name": e.bank_name, "bank_account": e.bank_account, "address": e.address,
            "user_id": str(e.user_id) if e.user_id else None,
            "user_username": linked_user.username if linked_user else None,
            "user_real_name": linked_user.real_name if linked_user else None,
            "remark": e.remark, "is_active": e.is_active,
            "created_at": e.created_at.isoformat() if e.created_at else None}
