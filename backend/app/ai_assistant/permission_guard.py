"""Permission guard — verify user has permission to use a tool."""

from fastapi import HTTPException, status
from app.models.user import User
from app.ai_assistant.tool_registry import AiToolDefinition


class PermissionGuard:
    def __init__(self, db):
        self.db = db

    async def check_permission(self, user: User, tool_def: AiToolDefinition) -> bool:
        if not tool_def.required_permission:
            return True
        for role in user.roles:
            for perm in role.permissions:
                if perm.code == tool_def.required_permission:
                    return True
        return False

    async def assert_permission(self, user: User, tool_def: AiToolDefinition):
        if not await self.check_permission(user, tool_def):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要「{tool_def.required_permission}」权限",
            )
