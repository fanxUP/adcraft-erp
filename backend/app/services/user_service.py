import secrets
from inspect import isawaitable
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permission_catalog import validate_permission_set
from app.core.password_policy import validate_new_password
from app.models.user_preferences import UserPreference
from app.models.employee import Employee
from app.repositories.user_repo import UserRepository
from app.utils.security import hash_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    @staticmethod
    def _validate_roles(role_ids: list[str], roles: list) -> None:
        """Validate role references and the effective capability composition.

        Role names are labels only.  The effective permission union is the
        security input, so custom roles behave exactly like built-in roles.
        """
        try:
            requested_ids = {str(UUID(role_id)) for role_id in role_ids}
        except (AttributeError, TypeError, ValueError):
            raise ValueError("角色编号格式不正确")
        loaded_ids = {str(role.id) for role in roles}
        if requested_ids != loaded_ids:
            raise ValueError("存在无效角色编号，未保存本次角色变更")

        effective_codes = {
            permission.code
            for role in roles
            for permission in getattr(role, "permissions", ())
        }
        issues = validate_permission_set(effective_codes)
        if issues:
            raise ValueError("；".join(dict.fromkeys(issue.message for issue in issues)))

    async def list_users(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        users, total = await self.repo.list_users(skip=skip, limit=page_size, keyword=keyword)
        employee_map = await self._linked_employee_map([u.id for u in users])
        user_list = []
        for u in users:
            user_list.append({
                "id": str(u.id),
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "email": u.email,
                "is_active": u.is_active,
                "must_change_password": getattr(u, "must_change_password", False),
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "roles": [r.name for r in u.roles],
                "linked_employee": employee_map.get(u.id),
            })
        return user_list, total

    async def get_user(self, user_id: UUID) -> dict | None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return None
        employee_map = await self._linked_employee_map([user.id])
        return {
            "id": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "is_active": user.is_active,
            "must_change_password": getattr(user, "must_change_password", False),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "roles": [r.name for r in user.roles],
            "linked_employee": employee_map.get(user.id),
        }

    async def _linked_employee_map(self, user_ids: list[UUID]) -> dict[UUID, dict]:
        if not user_ids:
            return {}
        result = await self.db.execute(
            select(Employee)
            .where(
                Employee.user_id.in_(user_ids),
                Employee.deleted_at.is_(None),
            )
            .order_by(Employee.created_at.desc())
        )
        return {
            employee.user_id: {
                "id": str(employee.id),
                "employee_no": employee.employee_no,
                "name": employee.name,
                "department": employee.department,
            }
            for employee in result.scalars().all()
            if employee.user_id is not None
        }

    async def create_user(self, data: dict) -> dict:
        existing = await self.repo.get_by_username(data["username"])
        if existing:
            raise ValueError("用户名已存在")

        role_ids = data.pop("role_ids", [])
        if role_ids:
            role_ids_uuid = [UUID(rid) for rid in role_ids]
            roles = await self.repo.get_roles(role_ids_uuid)
        else:
            roles = []
        self._validate_roles(role_ids, roles)

        data["password_hash"] = hash_password(data.pop("password"))
        user = await self.repo.create(data)
        preference = UserPreference(user_id=user.id)
        added = self.db.add(preference)
        if isawaitable(added):
            await added
        await self.db.flush()
        if roles:
            await self.repo.set_roles(user, roles)

        return await self.get_user(user.id)

    @staticmethod
    def _generate_initial_password() -> str:
        """Generate a one-time password without using employee identity data."""
        return secrets.token_urlsafe(12)

    @staticmethod
    def _validate_initial_password(
        password: str,
        *,
        employee_no: str,
        phone: str | None,
        id_card: str | None,
    ) -> None:
        validate_new_password(password)
        identity_values = {
            value.strip()
            for value in (employee_no, phone, id_card)
            if isinstance(value, str) and value.strip()
        }
        if password in identity_values:
            raise ValueError("初始密码不能使用工号、手机号或身份证号")

    async def provision_employee_user(
        self,
        *,
        employee_no: str,
        real_name: str,
        phone: str | None,
        role_ids: list[str] | None,
        initial_password: str | None,
        is_active: bool,
        id_card: str | None = None,
    ) -> dict:
        """Create the login side of an employee creation transaction.

        The caller creates the employee row in the same AsyncSession after
        this method returns.  No plaintext password is persisted or logged;
        the value is returned once so the employee administrator can hand it
        to the employee and require a first-login change.
        """
        employee_no = str(employee_no).strip()
        existing = await self.repo.get_by_username(employee_no, include_deleted=True)
        if existing:
            raise ValueError("工号已被现有账号占用，请先处理历史账号")

        role_ids = list(role_ids or [])
        try:
            role_ids_uuid = [UUID(role_id) for role_id in role_ids]
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("角色编号格式不正确") from exc
        roles = await self.repo.get_roles(role_ids_uuid) if role_ids_uuid else []
        self._validate_roles(role_ids, roles)

        password = initial_password or self._generate_initial_password()
        self._validate_initial_password(
            password,
            employee_no=employee_no,
            phone=phone,
            id_card=id_card,
        )
        user = await self.repo.create({
            "username": employee_no,
            "password_hash": hash_password(password),
            "real_name": real_name,
            "phone": phone,
            "is_active": bool(is_active),
            "must_change_password": True,
        })
        preference = UserPreference(user_id=user.id)
        added = self.db.add(preference)
        if isawaitable(added):
            await added
        await self.db.flush()
        if roles:
            await self.repo.set_roles(user, roles)
        return {"user": user, "initial_password": password}

    async def update_user(self, user_id: UUID, data: dict) -> dict:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        data = dict(data)
        requested_active = data.get("is_active")
        if requested_active is True and user.is_active is not True:
            linked_employee = await self._linked_employee(user.id)
            if linked_employee is not None and (
                getattr(linked_employee, "deleted_at", None) is not None
                or getattr(linked_employee, "employment_status", None) != "active"
                or getattr(linked_employee, "is_active", False) is not True
            ):
                raise ValueError("员工未在职或档案已停用，不能启用账号")
        should_disable = requested_active is False and user.is_active is True

        role_ids = data.pop("role_ids", None)
        roles = None
        if role_ids is not None:
            try:
                role_ids_uuid = [UUID(rid) for rid in role_ids]
            except (AttributeError, TypeError, ValueError):
                raise ValueError("角色编号格式不正确")
            roles = await self.repo.get_roles(role_ids_uuid)
            self._validate_roles(role_ids, roles)

        if should_disable:
            user.is_active = False
            user.token_version = (getattr(user, "token_version", 1) or 1) + 1

        # Validate the complete role set before changing any user fields.  A
        # rejected combination must not leave a partially mutated user in a
        # service call that is not wrapped by the HTTP transaction boundary.
        await self.repo.update(user, data)
        if roles is not None:
            await self.repo.set_roles(user, roles)

        return await self.get_user(user.id)

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        if await self._linked_employee(user.id) is not None:
            raise ValueError("员工账号由员工档案管理，不能删除，请先停用员工或账号")
        user.is_active = False
        user.token_version = (getattr(user, "token_version", 1) or 1) + 1
        await self.repo.soft_delete(user)
        return True

    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        validate_new_password(new_password)
        user = await self.repo.get_by_id(user_id)
        if not user:
            return False
        user.password_hash = hash_password(new_password)
        user.must_change_password = True
        user.token_version = (getattr(user, "token_version", 1) or 1) + 1
        await self.repo.update(user, {})
        return True

    async def _linked_employee(self, user_id: UUID):
        result = await self.db.execute(
            select(Employee)
            .where(Employee.user_id == user_id)
            .order_by(Employee.deleted_at.is_not(None), Employee.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
