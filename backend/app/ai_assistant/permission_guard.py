"""Permission guard — verify user has permission to use a tool."""

from fastapi import HTTPException, status

from app.ai_assistant.tool_registry import AiToolDefinition
from app.core.authorization import AuthorizationEvaluator
from app.models.user import User


class PermissionGuard:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _required_permissions(tool_def: AiToolDefinition) -> tuple[str, ...]:
        """Return the tool's complete authorization contract.

        ``required_permission`` remains the compatibility spelling used by
        existing tools.  A new tool can use ``required_permissions`` for an
        all-of requirement; if both are supplied, both are enforced.
        """

        return tuple(dict.fromkeys(
            ([tool_def.required_permission] if tool_def.required_permission else [])
            + list(tool_def.required_permissions)
        ))

    def _decision(self, user: User, tool_def: AiToolDefinition):
        permissions = self._required_permissions(tool_def)
        if not permissions:
            return None
        evaluator = AuthorizationEvaluator(user)
        return (
            evaluator.check(permissions[0])
            if len(permissions) == 1
            else evaluator.check_all(*permissions)
        )

    async def check_permission(self, user: User, tool_def: AiToolDefinition) -> bool:
        decision = self._decision(user, tool_def)
        return True if decision is None else decision.allowed

    async def assert_permission(self, user: User, tool_def: AiToolDefinition):
        decision = self._decision(user, tool_def)
        if decision is None:
            return
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.message or "当前账号没有执行该 AI 工具所需的全部权限",
            )
