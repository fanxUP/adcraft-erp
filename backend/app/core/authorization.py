"""Single authorization evaluator for routes, services and field policies."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.permission_catalog import (
    SENSITIVE_PERMISSIONS,
    PermissionValidationIssue,
    declared_permission_codes,
    expand_permission_dependencies,
    validate_permission_set,
)
from app.core.permissions import PERM_SYSTEM_SUPER_ADMIN, get_user_permission_codes


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str = "ALLOWED"
    message: str = ""
    required_permissions: tuple[str, ...] = ()
    missing_permissions: tuple[str, ...] = ()
    conflicting_permissions: tuple[str, ...] = ()


class AuthorizationEvaluator:
    """Evaluate effective permissions for one authenticated user.

    Roles are only an input to the permission union.  No role name is used to
    decide whether a request is allowed.
    """

    def __init__(self, user):
        self.user = user
        self.granted_permissions = get_user_permission_codes(user)

    @property
    def is_super_admin(self) -> bool:
        return PERM_SYSTEM_SUPER_ADMIN in self.granted_permissions

    def _conflict_permissions(self) -> tuple[str, ...]:
        issues = validate_permission_set(set(self.granted_permissions))
        return tuple(sorted({permission for issue in issues if issue.kind == "conflict" for permission in issue.permissions}))

    @staticmethod
    def _unknown_permissions(permission_codes) -> tuple[str, ...]:
        known = declared_permission_codes()
        return tuple(sorted(set(permission_codes) - known))

    @classmethod
    def _unknown_decision(cls, permission_codes) -> AuthorizationDecision | None:
        unknown = cls._unknown_permissions(permission_codes)
        if not unknown:
            return None
        return AuthorizationDecision(
            allowed=False,
            reason_code="AUTHZ_PERMISSION_UNKNOWN",
            message=f"权限目录未登记：{'、'.join(unknown)}，本次操作已拒绝",
            required_permissions=tuple(permission_codes),
            missing_permissions=unknown,
        )

    def check(self, permission_code: str) -> AuthorizationDecision:
        unknown = self._unknown_decision((permission_code,))
        if unknown:
            return unknown
        required = tuple(sorted(expand_permission_dependencies({permission_code})))
        if self.is_super_admin:
            return AuthorizationDecision(
                allowed=True,
                required_permissions=required,
            )

        if permission_code not in self.granted_permissions:
            return AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_PERMISSION_MISSING",
                message=f"当前账号没有「{permission_code}」权限，请联系管理员开通",
                required_permissions=required,
                missing_permissions=(permission_code,),
            )

        missing = tuple(permission for permission in required if permission not in self.granted_permissions)
        if missing:
            return AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_DEPENDENCY_MISSING",
                message=f"当前权限缺少前置能力：{'、'.join(missing)}，请联系管理员完善权限组合",
                required_permissions=required,
                missing_permissions=missing,
            )

        conflicts = self._conflict_permissions()
        if permission_code in SENSITIVE_PERMISSIONS and conflicts:
            return AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_COMBINATION_CONFLICT",
                message="当前权限组合存在安全冲突，任务执行人员不能查看价格或财务信息",
                required_permissions=required,
                conflicting_permissions=conflicts,
            )

        return AuthorizationDecision(
            allowed=True,
            required_permissions=required,
        )

    def check_all(self, *permission_codes: str) -> AuthorizationDecision:
        unknown = self._unknown_decision(permission_codes)
        if unknown:
            return unknown
        required = tuple(sorted(expand_permission_dependencies(set(permission_codes))))
        if self.is_super_admin:
            return AuthorizationDecision(allowed=True, required_permissions=required)

        missing = tuple(permission for permission in required if permission not in self.granted_permissions)
        if missing:
            direct_missing = tuple(permission for permission in permission_codes if permission not in self.granted_permissions)
            reason = "AUTHZ_PERMISSION_MISSING" if direct_missing else "AUTHZ_DEPENDENCY_MISSING"
            return AuthorizationDecision(
                allowed=False,
                reason_code=reason,
                message=f"当前账号缺少必要权限：{'、'.join(missing)}，请联系管理员开通",
                required_permissions=required,
                missing_permissions=missing,
            )

        conflicts = self._conflict_permissions()
        sensitive_requested = bool(set(permission_codes) & SENSITIVE_PERMISSIONS)
        if sensitive_requested and conflicts:
            return AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_COMBINATION_CONFLICT",
                message="当前权限组合存在安全冲突，任务执行人员不能查看价格或财务信息",
                required_permissions=required,
                conflicting_permissions=conflicts,
            )

        return AuthorizationDecision(allowed=True, required_permissions=required)

    def check_any(self, *permission_codes: str) -> AuthorizationDecision:
        if not permission_codes:
            return AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_PERMISSION_MISSING",
                message="未提供可用的授权能力",
            )
        known_codes = tuple(code for code in permission_codes if code in declared_permission_codes())
        if not known_codes:
            return self._unknown_decision(permission_codes) or AuthorizationDecision(
                allowed=False,
                reason_code="AUTHZ_PERMISSION_UNKNOWN",
                message="权限目录未登记，本次操作已拒绝",
            )
        if self.is_super_admin:
            return AuthorizationDecision(allowed=True, required_permissions=tuple(known_codes))
        decisions = [self.check(code) for code in known_codes]
        for decision in decisions:
            if decision.allowed:
                return decision
        missing = tuple(sorted({permission for decision in decisions for permission in decision.missing_permissions}))
        conflicts = tuple(sorted({permission for decision in decisions for permission in decision.conflicting_permissions}))
        reason = "AUTHZ_COMBINATION_CONFLICT" if conflicts else "AUTHZ_PERMISSION_MISSING"
        return AuthorizationDecision(
            allowed=False,
            reason_code=reason,
            message="当前账号没有可用的授权能力，请联系管理员开通",
            required_permissions=tuple(known_codes),
            missing_permissions=missing,
            conflicting_permissions=conflicts,
        )

    def can_view_field(self, permission_code: str) -> bool:
        return self.check(permission_code).allowed

    def explain(self, permission_code: str) -> dict[str, object]:
        decision = self.check(permission_code)
        return {
            "allowed": decision.allowed,
            "reason_code": decision.reason_code,
            "message": decision.message,
            "required_permissions": list(decision.required_permissions),
            "missing_permissions": list(decision.missing_permissions),
            "conflicting_permissions": list(decision.conflicting_permissions),
        }


def permission_validation_messages(permission_codes: set[str] | list[str] | tuple[str, ...]) -> list[PermissionValidationIssue]:
    """Public adapter used by role/user services and the admin preview API."""

    return validate_permission_set(permission_codes)
