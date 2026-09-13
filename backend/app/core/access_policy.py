"""Composable object-scope authorization facade.

``AuthorizationEvaluator`` remains the single source of truth for permission
codes, dependencies and conflicts.  This module adds the next dimension:
which records a permitted user may see.  Keeping scope decisions in a small,
framework-free object lets task queues, completed projects, dashboards and
attachments reuse the same contract without copying role-specific branches.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class DataScope(str, Enum):
    """Supported object visibility scopes.

    ``ALL`` is never implied by a normal read permission.  Callers must pass
    one or more explicit all-scope permissions in ``AccessRequest``.
    """

    ALL = "all"
    ASSIGNED = "assigned"
    SELF = "self"
    DEPARTMENT = "department"


@dataclass(frozen=True)
class AccessRequest:
    """A fully described access check for one resource or row."""

    permission: str
    scope: DataScope = DataScope.ALL
    all_scope_permissions: tuple[str, ...] = ()
    owner_user_ids: frozenset[str] = frozenset()
    assignee_user_ids: frozenset[str] = frozenset()
    department_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PolicyDecision:
    """Stable, plain-language result shared by services and tests."""

    allowed: bool
    reason_code: str = "ALLOWED"
    message: str = ""
    required_permissions: tuple[str, ...] = ()
    missing_permissions: tuple[str, ...] = ()
    matched_scope: str | None = None


def _normalize_id(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_ids(values: Iterable) -> frozenset[str]:
    return frozenset(
        normalized
        for value in values
        if (normalized := _normalize_id(value)) is not None
    )


class AuthorizationPolicy:
    """Combine capability authorization with an explicit data scope.

    The evaluator is imported lazily so this facade remains usable in pure
    unit tests and does not introduce a module cycle with the historical
    permission constants.  Production calls use the existing evaluator by
    default; tests may inject a compatible factory.
    """

    def __init__(
        self,
        viewer,
        *,
        evaluator_factory=None,
        viewer_department_ids: Iterable = (),
    ):
        self.viewer = viewer
        self._evaluator_factory = evaluator_factory
        self._viewer_department_ids = _normalize_ids(viewer_department_ids)
        self._evaluator = None

    @property
    def _authorization(self):
        if self.viewer is None:
            return None
        if self._evaluator is None:
            if self._evaluator_factory is not None:
                self._evaluator = self._evaluator_factory(self.viewer)
            else:
                from app.core.authorization import AuthorizationEvaluator

                self._evaluator = AuthorizationEvaluator(self.viewer)
        return self._evaluator

    @property
    def _is_super_admin(self) -> bool:
        return bool(getattr(self._authorization, "is_super_admin", False))

    def check(self, permission_code: str) -> PolicyDecision:
        """Check only the functional permission, without expanding scope."""
        if self.viewer is None:
            return PolicyDecision(allowed=True, required_permissions=(permission_code,))

        decision = self._authorization.check(permission_code)
        return PolicyDecision(
            allowed=decision.allowed,
            reason_code="ALLOWED" if decision.allowed else decision.reason_code,
            message=decision.message,
            required_permissions=tuple(decision.required_permissions),
            missing_permissions=tuple(decision.missing_permissions),
        )

    def allows(self, permission_code: str) -> bool:
        return self.check(permission_code).allowed

    def check_any(self, permission_codes: Iterable[str]) -> PolicyDecision:
        codes = tuple(dict.fromkeys(permission_codes))
        if self.viewer is None:
            return PolicyDecision(allowed=True, required_permissions=codes)
        if not codes:
            return PolicyDecision(
                allowed=False,
                reason_code="AUTHZ_SCOPE_PERMISSION_MISSING",
                message="没有配置全量数据权限，不能查看全部数据",
            )

        decision = self._authorization.check_any(*codes)
        return PolicyDecision(
            allowed=decision.allowed,
            reason_code="ALLOWED" if decision.allowed else decision.reason_code,
            message=decision.message,
            required_permissions=tuple(decision.required_permissions),
            missing_permissions=tuple(decision.missing_permissions),
        )

    def allows_all_scope(self, scope_permissions: Iterable[str]) -> bool:
        """Return whether the viewer has a dedicated all-records capability."""
        if self.viewer is None or self._is_super_admin:
            return True
        return self.check_any(scope_permissions).allowed

    def check_access(self, request: AccessRequest) -> PolicyDecision:
        """Evaluate capability and object scope without leaking row details."""
        try:
            scope = request.scope if isinstance(request.scope, DataScope) else DataScope(request.scope)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"未知数据范围: {request.scope}") from exc

        permission_decision = self.check(request.permission)
        if not permission_decision.allowed:
            return permission_decision
        if self.viewer is None or self._is_super_admin:
            return PolicyDecision(
                allowed=True,
                required_permissions=permission_decision.required_permissions,
                matched_scope=scope.value,
            )

        if scope is DataScope.ALL:
            if not request.all_scope_permissions:
                return PolicyDecision(
                    allowed=False,
                    reason_code="AUTHZ_SCOPE_PERMISSION_MISSING",
                    message="当前只有功能查看权限，未授予全部数据查看权限",
                    required_permissions=permission_decision.required_permissions,
                    matched_scope=scope.value,
                )
            scope_decision = self.check_any(request.all_scope_permissions)
            if not scope_decision.allowed:
                return PolicyDecision(
                    allowed=False,
                    reason_code="AUTHZ_SCOPE_PERMISSION_MISSING",
                    message="当前只有功能查看权限，未授予全部数据查看权限",
                    required_permissions=tuple(
                        dict.fromkeys(
                            permission_decision.required_permissions
                            + scope_decision.required_permissions
                        )
                    ),
                    missing_permissions=scope_decision.missing_permissions,
                    matched_scope=scope.value,
                )
            return PolicyDecision(
                allowed=True,
                required_permissions=tuple(
                    dict.fromkeys(
                        permission_decision.required_permissions
                        + scope_decision.required_permissions
                    )
                ),
                matched_scope=scope.value,
            )

        viewer_id = _normalize_id(getattr(self.viewer, "id", None))
        if viewer_id is None:
            return PolicyDecision(
                allowed=False,
                reason_code="AUTHZ_SCOPE_SUBJECT_MISSING",
                message="当前账号缺少有效身份，不能判断数据归属",
                required_permissions=permission_decision.required_permissions,
                matched_scope=scope.value,
            )

        if scope is DataScope.SELF:
            subject_ids = _normalize_ids(request.owner_user_ids)
            if viewer_id not in subject_ids:
                return self._scope_denied(permission_decision, scope)
        elif scope is DataScope.ASSIGNED:
            subject_ids = _normalize_ids(request.assignee_user_ids)
            if viewer_id not in subject_ids:
                return self._scope_denied(permission_decision, scope)
        elif scope is DataScope.DEPARTMENT:
            viewer_departments = self._viewer_department_ids | _normalize_ids(
                getattr(self.viewer, "department_ids", ())
            )
            record_departments = _normalize_ids(request.department_ids)
            if not viewer_departments.intersection(record_departments):
                return self._scope_denied(permission_decision, scope)

        return PolicyDecision(
            allowed=True,
            required_permissions=permission_decision.required_permissions,
            matched_scope=scope.value,
        )

    @staticmethod
    def _scope_denied(
        permission_decision: PolicyDecision,
        scope: DataScope,
    ) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason_code="AUTHZ_SCOPE_DENIED",
            message="当前数据不在你的可见范围内",
            required_permissions=permission_decision.required_permissions,
            matched_scope=scope.value,
        )

    def allows_access(self, request: AccessRequest) -> bool:
        return self.check_access(request).allowed
