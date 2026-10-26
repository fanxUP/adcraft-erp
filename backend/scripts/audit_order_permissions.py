"""Read-only role/user inventory before releasing the order permission changes.

Run with the deployment's usual DATABASE_URL. Outputs grants and composition
issues only, never credentials. Does not repair or reassign permissions.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.core.database import async_session_maker, engine
from app.core.permission_catalog import RETIRED_QUOTE_PERMISSIONS, validate_permission_set
from app.core.permissions import get_user_permission_codes
from app.models.user import Role, User


def composition(codes):
    return {
        "grants": sorted(codes),
        "retired_grants": sorted(set(codes) & RETIRED_QUOTE_PERMISSIONS),
        "issues": [{"kind": issue.kind, "code": issue.code, "message": issue.message}
                   for issue in validate_permission_set(codes)],
    }


async def main():
    try:
        async with async_session_maker() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            roles = (await db.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.name))).all()
            users = (await db.scalars(select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                                     .where(User.is_active.is_(True), User.deleted_at.is_(None)).order_by(User.username))).all()
            print(json.dumps({"mode": "read_only", "roles": [{"id": str(role.id), "name": role.name,
                **composition({permission.code for permission in role.permissions})} for role in roles],
                "users": [{"id": str(user.id), "username": user.username, "roles": [role.name for role in user.roles],
                    **composition(get_user_permission_codes(user))} for user in users]}, ensure_ascii=False, indent=2))
            await db.rollback()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
