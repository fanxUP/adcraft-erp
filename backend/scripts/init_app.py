"""Initialize the application with seed data.

Called during Docker startup after `alembic upgrade head`.
Inserts default roles, an admin user, and all permissions.

Idempotent — safe to run multiple times.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Ensure the backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.models.user import Role, Permission, User, user_roles
from app.utils.security import hash_password


ROLES = [
    {"name": "admin", "description": "系统管理员，拥有所有权限"},
    {"name": "sales", "description": "销售员，管理客户和报价"},
    {"name": "designer", "description": "设计师，处理设计任务"},
    {"name": "production", "description": "制作人员，处理制作任务"},
    {"name": "installer", "description": "安装人员，处理安装任务"},
    {"name": "finance", "description": "财务人员，管理收款和对账"},
]

ADMIN_USER = {
    "username": "admin",
    "password": "admin123",
    "real_name": "系统管理员",
}


async def init_app():
    """Run all seed operations idempotently."""
    async with async_session_maker() as session:
        # 1. Seed roles
        existing_roles: dict[str, Role] = {}
        result = await session.execute(select(Role))
        seen_names = {r.name for r in result.scalars().all()}

        for r_def in ROLES:
            if r_def["name"] not in seen_names:
                role = Role(id=uuid4(), name=r_def["name"], description=r_def["description"])
                session.add(role)
                existing_roles[r_def["name"]] = role
                print(f"  + Role: {r_def['name']}")
            else:
                print(f"  ✓ Role exists: {r_def['name']}")

        await session.flush()

        # Re-fetch roles to get all IDs (including pre-existing ones from init-db.sh)
        result = await session.execute(select(Role))
        roles_by_name: dict[str, Role] = {r.name: r for r in result.scalars().all()}

        # 2. Seed admin user
        result = await session.execute(
            select(User).where(User.username == ADMIN_USER["username"])
        )
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                id=uuid4(),
                username=ADMIN_USER["username"],
                password_hash=hash_password(ADMIN_USER["password"]),
                real_name=ADMIN_USER["real_name"],
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()
            print(f"  + Admin user created: {ADMIN_USER['username']}")
        else:
            print(f"  ✓ Admin user exists: {ADMIN_USER['username']}")

        # 3. Assign admin role to admin user
        admin_role = roles_by_name.get("admin")
        if admin_role:
            # Check via explicit query to avoid lazy-load in async context
            result = await session.execute(
                select(user_roles).where(
                    user_roles.c.user_id == admin_user.id,
                    user_roles.c.role_id == admin_role.id,
                )
            )
            already_assigned = result.first() is not None
            if not already_assigned:
                await session.execute(
                    user_roles.insert().values(user_id=admin_user.id, role_id=admin_role.id)
                )
                await session.flush()
                print("  + Admin role assigned to admin user")
            else:
                print("  ✓ Admin already has admin role")

        # 4. Seed permissions (import the logic from seed_permissions.py)
        from scripts.seed_permissions import ALL_PERMISSIONS, ROLE_PERMISSION_MAP

        # Upsert permissions
        result = await session.execute(select(Permission))
        existing_perms: dict[str, Permission] = {p.code: p for p in result.scalars().all()}

        for p_def in ALL_PERMISSIONS:
            if p_def["code"] not in existing_perms:
                perm = Permission(
                    id=uuid4(),
                    code=p_def["code"],
                    name=p_def["name"],
                    description=p_def.get("description"),
                )
                session.add(perm)
                existing_perms[p_def["code"]] = perm

        await session.flush()

        # Map permissions to roles
        for role_name, role in roles_by_name.items():
            codes = ROLE_PERMISSION_MAP.get(role_name, [])
            target_perms = [existing_perms[c] for c in codes if c in existing_perms]
            role.permissions = target_perms

        await session.flush()
        await session.commit()

        # Summary
        role_counts = {r.name: len(r.permissions) for r in roles_by_name.values()}
        print(f"\n🎉 Initialization complete!")
        for name, count in role_counts.items():
            print(f"  → {name}: {count} permissions")
        print(f"  → Admin login: {ADMIN_USER['username']} / {ADMIN_USER['password']}")


async def main():
    print("🌱 Initializing application data...\n")
    try:
        await init_app()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
