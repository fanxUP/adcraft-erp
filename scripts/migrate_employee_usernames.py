#!/usr/bin/env python3
"""Audit and, only when explicitly requested, align bound usernames to employee_no.

The default mode is read-only.  ``--apply-bound`` changes only unambiguous
one-to-one bindings in place, preserving the User UUID, password hash, roles,
operation history and all business references.  It never guesses an employee
for an unbound user and never creates a password or account for an unbound
employee.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session_maker, engine  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.user import User  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-bound",
        action="store_true",
        help="apply only conflict-free bound-account username changes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print the audit result as JSON",
    )
    return parser.parse_args()


async def build_plan(session) -> dict:
    employee_result = await session.execute(
        select(Employee)
        .where(Employee.deleted_at.is_(None))
        .order_by(Employee.employee_no.asc())
    )
    user_result = await session.execute(select(User).order_by(User.username.asc()))
    employees = list(employee_result.scalars().all())
    users = list(user_result.scalars().all())
    users_by_id = {user.id: user for user in users}
    users_by_username = {user.username: user for user in users}

    unchanged: list[dict] = []
    rename: list[dict] = []
    conflicts: list[dict] = []
    missing_users: list[dict] = []
    unbound_employees: list[dict] = []

    for employee in employees:
        base = {
            "employee_no": employee.employee_no,
            "employee_name": employee.name,
        }
        if employee.user_id is None:
            collision = users_by_username.get(employee.employee_no)
            item = {**base, "collision": bool(collision)}
            if collision is not None:
                item["collision_username"] = collision.username
                item["collision_user_id"] = str(collision.id)
            unbound_employees.append(item)
            continue

        user = users_by_id.get(employee.user_id)
        if user is None:
            missing_users.append({**base, "user_id": str(employee.user_id)})
            continue
        if user.username == employee.employee_no:
            unchanged.append({**base, "user_id": str(user.id)})
            continue

        collision = users_by_username.get(employee.employee_no)
        if collision is not None and collision.id != user.id:
            conflicts.append(
                {
                    **base,
                    "user_id": str(user.id),
                    "current_username": user.username,
                    "conflict_user_id": str(collision.id),
                    "conflict_username": collision.username,
                }
            )
            continue
        rename.append(
            {
                **base,
                "user_id": str(user.id),
                "current_username": user.username,
                "target_username": employee.employee_no,
            }
        )

    bound_user_ids = {employee.user_id for employee in employees if employee.user_id}
    legacy_users = [
        {"user_id": str(user.id), "username": user.username}
        for user in users
        if user.id not in bound_user_ids
        and user.username != "admin"
        and user.deleted_at is None
    ]
    unbound_collisions = [
        item for item in unbound_employees if item.get("collision")
    ]
    return {
        "mode": "dry-run",
        "counts": {
            "employees": len(employees),
            "users": len(users),
            "unchanged": len(unchanged),
            "rename": len(rename),
            "conflicts": len(conflicts),
            "missing_users": len(missing_users),
            "unbound_employees": len(unbound_employees),
            "unbound_collisions": len(unbound_collisions),
            "legacy_users": len(legacy_users),
        },
        "unchanged": unchanged,
        "rename": rename,
        "conflicts": conflicts,
        "missing_users": missing_users,
        "unbound_employees": unbound_employees,
        "unbound_collisions": unbound_collisions,
        "legacy_users": legacy_users,
    }


async def run(apply_bound: bool) -> tuple[dict, int]:
    async with async_session_maker() as session:
        plan = await build_plan(session)
        plan["mode"] = "apply-bound" if apply_bound else "dry-run"
        if plan["conflicts"] or plan["missing_users"] or plan["unbound_collisions"]:
            await session.rollback()
            return plan, 2
        if apply_bound:
            users = {
                str(user.id): user
                for user in (
                    await session.execute(select(User))
                ).scalars().all()
            }
            for item in plan["rename"]:
                users[item["user_id"]].username = item["target_username"]
            await session.flush()
            await session.commit()
        else:
            await session.rollback()
        return plan, 0


async def main() -> int:
    args = _parse_args()
    try:
        plan, status = await run(args.apply_bound)
    finally:
        await engine.dispose()
    if args.as_json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"mode={plan['mode']}")
        for key, value in plan["counts"].items():
            print(f"{key}={value}")
        if plan["conflicts"]:
            print("conflicts:")
            for item in plan["conflicts"]:
                print(json.dumps(item, ensure_ascii=False))
        if plan["missing_users"]:
            print("missing_users:")
            for item in plan["missing_users"]:
                print(json.dumps(item, ensure_ascii=False))
        if plan["unbound_employees"]:
            print("unbound_employees:")
            for item in plan["unbound_employees"]:
                print(json.dumps(item, ensure_ascii=False))
    if status == 0 and args.apply_bound:
        print(f"applied_bound_renames={plan['counts']['rename']}")
    return status


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
