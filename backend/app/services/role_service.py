from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permission_catalog import (
    PermissionDefinition,
    PermissionValidationIssue,
    get_permission_definition,
    validate_permission_set,
)
from app.core.permissions import (
    ROLE_ADMIN,
    ROLE_DESIGNER,
    ROLE_FINANCE,
    ROLE_INSTALLER,
    ROLE_OUTSOURCE_MANAGER,
    ROLE_PRODUCTION,
    ROLE_RESOURCE_MANAGER,
    ROLE_SALES,
)
from app.repositories.role_repo import RoleRepository


BUILTIN_ROLE_NAMES = frozenset({
    ROLE_ADMIN,
    ROLE_SALES,
    ROLE_DESIGNER,
    ROLE_PRODUCTION,
    ROLE_INSTALLER,
    ROLE_FINANCE,
    ROLE_RESOURCE_MANAGER,
    ROLE_OUTSOURCE_MANAGER,
})


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RoleRepository(db)

    async def list_roles(self) -> list[dict]:
        roles = await self.repo.list_roles()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "permissions": [self._serialize_permission(p) for p in r.permissions],
            }
            for r in roles
        ]

    @staticmethod
    def _serialize_permission(permission) -> dict:
        """Return one permission with semantic metadata and compatibility keys."""
        try:
            definition = get_permission_definition(permission.code)
        except KeyError:
            # Keep stale/manual catalog rows visible to administrators so they
            # can remove them; never let one unknown historical code crash the
            # whole role-management page.
            definition = PermissionDefinition(
                code=permission.code,
                module="unknown",
                resource="unknown",
                action="unknown",
                kind="unknown",
                sensitivity="security",
            )
        def metadata(name: str, fallback):
            value = getattr(permission, name, None)
            return value if isinstance(value, (str, int)) and value != "" else fallback

        return {
            "id": str(permission.id),
            "code": permission.code,
            "name": permission.name,
            "description": getattr(permission, "description", None) or "",
            "module": metadata("module", definition.module),
            "resource": metadata("resource", definition.resource),
            "action": metadata("action", definition.action),
            "kind": metadata("kind", definition.kind),
            "sensitivity": metadata("sensitivity", definition.sensitivity),
            "status": metadata("status", "active"),
            "sort_order": metadata("sort_order", 0),
            "requires": list(definition.requires),
        }

    async def create_role(self, name: str, description: str | None = None) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("角色名称不能为空")
        if name in BUILTIN_ROLE_NAMES:
            raise ValueError("该名称属于系统内置角色，不能重复创建")
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValueError("角色名称已存在")
        role = await self.repo.create(name, description)
        return {"id": str(role.id), "name": role.name, "description": role.description, "permissions": []}

    async def update_role(self, role_id: UUID, data: dict) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        requested_name = data.get("name")
        if requested_name:
            requested_name = requested_name.strip()
            if requested_name != role.name:
                if role.name in BUILTIN_ROLE_NAMES:
                    raise ValueError("系统内置角色不能重命名")
                if requested_name in BUILTIN_ROLE_NAMES:
                    raise ValueError("该名称属于系统内置角色，不能使用")
                duplicate = await self.repo.get_by_name(requested_name)
                if duplicate and duplicate.id != role.id:
                    raise ValueError("角色名称已存在")
                data = {**data, "name": requested_name}
        role = await self.repo.update(role, data)
        return {"id": str(role.id), "name": role.name, "description": role.description}

    async def delete_role(self, role_id: UUID) -> None:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        if role.name in BUILTIN_ROLE_NAMES:
            raise ValueError("系统内置角色不能删除")
        bound_users = await self._get_bound_users(role)
        if bound_users:
            raise ValueError("该角色仍绑定在职用户，请先移除用户绑定后再删除")
        await self.repo.delete(role)

    async def set_role_permissions(self, role_id: UUID, permission_ids: list[str]) -> dict:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        perms = await self._resolve_permissions(permission_ids)
        existing_codes = {permission.code for permission in getattr(role, "permissions", ()) or ()}
        status_issues = self._permission_status_issues(perms, existing_codes)
        issues = validate_permission_set({permission.code for permission in perms})
        issues.extend(status_issues)
        issues.extend(await self._bound_user_issues(role, perms))
        if issues:
            # Return all errors in one response so the admin can fix the
            # composition without repeated save-and-fail cycles.
            raise ValueError("；".join(dict.fromkeys(issue.message for issue in issues)))
        requested_codes = {permission.code for permission in perms}
        await self.repo.set_permissions(role, perms)
        return {
            "id": str(role.id),
            "name": role.name,
            "permissions": [self._serialize_permission(p) for p in role.permissions],
            "added_permissions": sorted(requested_codes - existing_codes),
            "removed_permissions": sorted(existing_codes - requested_codes),
        }

    async def preview_role_permissions(self, role_id: UUID, permission_ids: list[str]) -> dict:
        """Validate a role composition without changing the database."""
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        perms = await self._resolve_permissions(permission_ids)
        existing_codes = {permission.code for permission in getattr(role, "permissions", ()) or ()}
        status_issues = self._permission_status_issues(perms, existing_codes)
        issues = validate_permission_set({permission.code for permission in perms})
        issues.extend(status_issues)
        issues.extend(await self._bound_user_issues(role, perms))
        requested_codes = {permission.code for permission in perms}
        users = await self._get_bound_users(role)
        return {
            "role_id": str(role.id),
            "valid": not issues,
            "issues": [
                {
                    "kind": issue.kind,
                    "code": issue.code,
                    "message": issue.message,
                    "permissions": list(issue.permissions),
                }
                for issue in issues
            ],
            "added_permissions": sorted(requested_codes - existing_codes),
            "removed_permissions": sorted(existing_codes - requested_codes),
            "affected_user_count": len(users) if hasattr(users, "__len__") else 0,
            "permissions": [self._serialize_permission(permission) for permission in perms],
        }

    async def _get_bound_users(self, role) -> list:
        """Return users affected by a role change, with a test-friendly fallback."""
        repo_loader = getattr(self.repo, "get_bound_users", None)
        if repo_loader is not None:
            users = await repo_loader(role.id)
            return list(users or [])
        return list(getattr(role, "users", ()) or ())

    async def _bound_user_issues(self, role, requested_permissions: list) -> list:
        """Simulate the new role against every active user's other roles."""
        requested_codes = {permission.code for permission in requested_permissions}
        issues: list = []
        for user in await self._get_bound_users(role):
            effective_codes: set[str] = set()
            for assigned_role in getattr(user, "roles", ()) or ():
                if str(getattr(assigned_role, "id", "")) == str(role.id):
                    effective_codes.update(requested_codes)
                else:
                    effective_codes.update(
                        permission.code
                        for permission in getattr(assigned_role, "permissions", ()) or ()
                    )
            for issue in validate_permission_set(effective_codes):
                issues.append(type(issue)(
                    kind=issue.kind,
                    code=issue.code,
                    message=f"角色变更会影响已绑定用户，{issue.message}",
                    permissions=issue.permissions,
                ))
        return issues

    async def _resolve_permissions(self, permission_ids: list[str]):
        try:
            perm_uuids = list(dict.fromkeys(UUID(pid) for pid in permission_ids))
        except (AttributeError, TypeError, ValueError):
            raise ValueError("权限编号格式不正确")
        perms = await self.repo.get_permissions_by_ids(perm_uuids)
        if len(perms) != len(perm_uuids):
            raise ValueError("存在无效权限编号，未保存本次变更")
        return perms

    @staticmethod
    def _permission_status_issues(
        perms: list,
        existing_codes: set[str] | frozenset[str] = frozenset(),
    ) -> list[PermissionValidationIssue]:
        issues = []
        for permission in perms:
            status = getattr(permission, "status", None)
            if (
                isinstance(status, str)
                and status
                and status != "active"
                and permission.code not in existing_codes
            ):
                issues.append(PermissionValidationIssue(
                    kind="deprecated_permission",
                    code=permission.code,
                    message=f"权限「{permission.code}」已停用，不能新分配",
                    permissions=(permission.code,),
                ))
        return issues

    async def list_permissions(self) -> list[dict]:
        perms = await self.repo.list_permissions()
        return [self._serialize_permission(p) for p in perms]
