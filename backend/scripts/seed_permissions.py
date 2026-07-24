"""Seed permissions and role-permission mappings.

Usage:
    cd backend && python scripts/seed_permissions.py

This script reads the DATABASE_URL from the project config,
creates all permission records (idempotent), and maps them
to the six built-in roles: admin, sales, designer, production, installer, finance.
"""

import asyncio
import sys
from pathlib import Path

# Ensure the backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.models.user import Permission, Role, role_permissions
from sqlalchemy import select, delete


# ── Define all permissions ────────────────────────────────────────────────

ALL_PERMISSIONS: list[dict[str, str | None]] = [
    # System
    {"code": "system:logs", "name": "查看操作日志", "description": "查看系统操作日志"},
    # Backup
    {"code": "backup:create", "name": "创建备份", "description": "创建数据库和文件备份"},
    {"code": "backup:read", "name": "查看备份", "description": "查看备份文件列表"},
    {"code": "backup:restore", "name": "恢复备份", "description": "从备份文件恢复数据"},
    {"code": "backup:delete", "name": "删除备份", "description": "删除备份文件"},
    # User management
    {"code": "user:read", "name": "查看用户", "description": "查看用户列表和详情"},
    {"code": "user:create", "name": "创建用户", "description": "创建新用户"},
    {"code": "user:update", "name": "编辑用户", "description": "编辑用户信息"},
    {"code": "user:delete", "name": "删除用户", "description": "删除用户"},
    # Customer
    {"code": "customer:read", "name": "查看客户", "description": "查看客户列表和详情"},
    {"code": "customer:create", "name": "创建客户", "description": "创建新客户"},
    {"code": "customer:update", "name": "编辑客户", "description": "编辑客户信息"},
    {"code": "customer:delete", "name": "删除客户", "description": "删除客户"},
    # Product
    {"code": "product:read", "name": "查看产品", "description": "查看产品列表和详情"},
    {"code": "product:create", "name": "创建产品", "description": "创建新产品"},
    {"code": "product:update", "name": "编辑产品", "description": "编辑产品信息"},
    {"code": "product:delete", "name": "删除产品", "description": "删除产品"},
    # Material
    {"code": "material:read", "name": "查看材质", "description": "查看材质列表和详情"},
    {"code": "material:create", "name": "创建材质", "description": "创建新材质"},
    {"code": "material:update", "name": "编辑材质", "description": "编辑材质信息"},
    {"code": "material:delete", "name": "删除材质", "description": "删除材质"},
    # Process
    {"code": "process:read", "name": "查看工艺", "description": "查看工艺列表和详情"},
    {"code": "process:create", "name": "创建工艺", "description": "创建新工艺"},
    {"code": "process:update", "name": "编辑工艺", "description": "编辑工艺信息"},
    {"code": "process:delete", "name": "删除工艺", "description": "删除工艺"},
    # Quote
    {"code": "quote:read", "name": "查看报价", "description": "查看报价列表和详情"},
    {"code": "quote:create", "name": "创建报价", "description": "创建新报价"},
    {"code": "quote:update", "name": "编辑报价", "description": "编辑报价信息"},
    {"code": "quote:delete", "name": "删除报价", "description": "删除报价"},
    {"code": "quote:confirm", "name": "确认报价", "description": "确认报价单"},
    {"code": "quote:convert", "name": "转为订单", "description": "将报价转为订单"},
    # Order
    {"code": "order:read", "name": "查看订单", "description": "查看订单列表和详情"},
    {"code": "order:create", "name": "创建订单", "description": "创建新订单"},
    {"code": "order:update", "name": "编辑订单", "description": "编辑订单信息"},
    {"code": "order:delete", "name": "删除订单", "description": "删除订单"},
    {"code": "order:change_status", "name": "变更订单状态", "description": "变更订单状态"},
    # Design task
    {"code": "design_task:read", "name": "查看设计任务", "description": "查看设计任务列表和详情"},
    {"code": "design_task:create", "name": "创建设计任务", "description": "创建新设计任务"},
    {"code": "design_task:update", "name": "编辑设计任务", "description": "编辑设计任务信息"},
    {"code": "design_task:change_status", "name": "变更设计状态", "description": "变更设计任务状态"},
    # Production task
    {"code": "production_task:read", "name": "查看制作任务", "description": "查看制作任务列表和详情"},
    {"code": "production_task:create", "name": "创建制作任务", "description": "创建新制作任务"},
    {"code": "production_task:update", "name": "编辑制作任务", "description": "编辑制作任务信息"},
    {"code": "production_task:change_status", "name": "变更制作状态", "description": "变更制作任务状态"},
    # Installation task
    {"code": "installation_task:read", "name": "查看安装任务", "description": "查看安装任务列表和详情"},
    {"code": "installation_task:create", "name": "创建安装任务", "description": "创建新安装任务"},
    {"code": "installation_task:update", "name": "编辑安装任务", "description": "编辑安装任务信息"},
    {"code": "installation_task:change_status", "name": "变更安装状态", "description": "变更安装任务状态"},
    # Payment
    {"code": "payment:read", "name": "查看收款", "description": "查看收款记录"},
    {"code": "payment:create", "name": "创建收款", "description": "创建收款记录"},
    {"code": "payment:void", "name": "作废收款", "description": "作废收款记录"},
    # Statement
    {"code": "statement:read", "name": "查看对账单", "description": "查看对账单列表和详情"},
    {"code": "statement:create", "name": "创建对账单", "description": "创建新对账单"},
    {"code": "statement:confirm", "name": "确认对账单", "description": "确认对账单"},
    # Expense
    {"code": "expense:read", "name": "查看支出", "description": "查看支出记录"},
    {"code": "expense:create", "name": "创建支出", "description": "创建支出记录"},
    {"code": "expense:update", "name": "编辑支出", "description": "编辑支出信息"},
    {"code": "expense:delete", "name": "删除支出", "description": "删除支出"},
    # Inventory
    {"code": "inventory:read", "name": "查看库存", "description": "查看库存物料"},
    {"code": "inventory:create", "name": "创建物料", "description": "创建新物料"},
    {"code": "inventory:update", "name": "编辑物料", "description": "编辑物料信息"},
    {"code": "inventory:stock_in", "name": "入库", "description": "物料入库操作"},
    {"code": "inventory:stock_out", "name": "出库", "description": "物料出库操作"},
    # Outsource
    {"code": "outsource:read", "name": "查看外协", "description": "查看外协信息"},
    {"code": "outsource:create", "name": "创建外协", "description": "创建外协商/任务/付款"},
    {"code": "outsource:update", "name": "编辑外协", "description": "编辑外协信息"},
    {"code": "outsource:delete", "name": "删除外协", "description": "删除外协记录"},
    # Report
    {"code": "report:read", "name": "查看报表", "description": "查看销售报表"},
    # Vehicle
    {"code": "vehicle:read", "name": "查看车辆", "description": "查看车辆和司机档案"},
    {"code": "vehicle:create", "name": "创建车辆", "description": "新增车辆和司机"},
    {"code": "vehicle:update", "name": "编辑车辆", "description": "编辑车辆和司机信息、停用/启用/报废"},
    {"code": "finance:review", "name": "财务审核", "description": "审核油费、维修保养等车辆费用"},
    # Aerial work platform (高空作业车台账)
    {"code": "aerial:read", "name": "查看高空车台账", "description": "查看高空作业车档案、台账、驾驶员、费用等信息"},
    {"code": "aerial:create", "name": "创建高空车台账", "description": "创建高空车台账记录、驾驶员、费用、安全检查等"},
    {"code": "aerial:update", "name": "编辑高空车台账", "description": "编辑和审核高空车台账记录"},
    {"code": "aerial:delete", "name": "删除高空车台账", "description": "作废台账或删除附件"},
    {"code": "aerial:finance", "name": "高空车财务操作", "description": "报销驾驶员垫付费用、发放工资"},
    {"code": "aerial:wage", "name": "管理高空车工资", "description": "创建和管理驾驶员工资记录"},
    {"code": "aerial:approve", "name": "审核高空车台账", "description": "审批和驳回台账记录"},
    # AI Features
    {"code": "ai_quote:read", "name": "AI报价助手", "description": "使用AI智能报价功能"},
    {"code": "ai_anomaly:read", "name": "智能异常提醒", "description": "查看AI异常检测结果"},
    {"code": "ai_knowledge:read", "name": "报价知识库", "description": "使用AI报价知识库"},
    {"code": "ai_report:read", "name": "智能经营报告", "description": "查看AI生成的经营报告"},
]

# ── Role-to-permission mapping ─────────────────────────────────────────────

# admin gets ALL permissions
# Others get role-appropriate subsets

ROLE_PERMISSION_MAP: dict[str, list[str]] = {
    "admin": [p["code"] for p in ALL_PERMISSIONS],
    "sales": [
        "customer:read", "customer:create", "customer:update", "customer:delete",
        "product:read",
        "material:read",
        "process:read",
        "quote:read", "quote:create", "quote:update", "quote:delete", "quote:confirm", "quote:convert",
        "order:read", "order:create", "order:update", "order:change_status",
        "payment:read", "payment:create",
        "expense:read",
        "report:read",
        "ai_quote:read", "ai_anomaly:read", "ai_knowledge:read", "ai_report:read",
        "vehicle:read",
        "aerial:read",
    ],
    "designer": [
        "customer:read",
        "product:read", "product:create", "product:update", "product:delete",
        "material:read", "material:create", "material:update", "material:delete",
        "process:read", "process:create", "process:update", "process:delete",
        "design_task:read", "design_task:create", "design_task:update", "design_task:change_status",
        "production_task:read",
        "installation_task:read",
    ],
    "production": [
        "customer:read",
        "product:read", "product:create", "product:update", "product:delete",
        "material:read", "material:create", "material:update", "material:delete",
        "process:read", "process:create", "process:update", "process:delete",
        "production_task:read", "production_task:create", "production_task:update", "production_task:change_status",
        "inventory:read", "inventory:create", "inventory:update", "inventory:stock_in", "inventory:stock_out",
        "vehicle:read", "vehicle:create", "vehicle:update",
        "aerial:read", "aerial:create", "aerial:update", "aerial:wage",
    ],
    "installer": [
        "customer:read",
        "installation_task:read", "installation_task:create", "installation_task:update", "installation_task:change_status",
        "vehicle:read", "vehicle:update",
        "aerial:read", "aerial:create", "aerial:update",
    ],
    "finance": [
        "customer:read",
        "order:read",
        "payment:read", "payment:create", "payment:void",
        "statement:read", "statement:create", "statement:confirm",
        "expense:read", "expense:create", "expense:update", "expense:delete",
        "report:read",
        "ai_quote:read", "ai_anomaly:read", "ai_knowledge:read", "ai_report:read",
        "vehicle:read", "finance:review",
        "aerial:read", "aerial:finance", "aerial:approve",
    ],
}

# ── Roles referenced by the init-db.sh script ──────────────────────────────
ROLE_NAMES = ["admin", "sales", "designer", "production", "installer", "finance"]


async def seed_permissions():
    """Create or refresh all permissions and role-permission mappings."""
    async with async_session_maker() as session:
        # 1. Fetch existing roles
        result = await session.execute(select(Role).where(Role.name.in_(ROLE_NAMES)))
        existing_roles: dict[str, Role] = {r.name: r for r in result.scalars().all()}

        if len(existing_roles) < len(ROLE_NAMES):
            missing = set(ROLE_NAMES) - set(existing_roles.keys())
            print(f"⚠️  Missing roles (run init-db.sh first): {', '.join(sorted(missing))}")
            if not existing_roles:
                print("❌ No roles found. Aborting.")
                return

        # 2. Upsert permissions (insert if code doesn't exist)
        result = await session.execute(select(Permission))
        existing_perms: dict[str, Permission] = {p.code: p for p in result.scalars().all()}

        created_count = 0
        for p_def in ALL_PERMISSIONS:
            if p_def["code"] not in existing_perms:
                perm = Permission(
                    code=p_def["code"],
                    name=p_def["name"],
                    description=p_def.get("description"),
                )
                session.add(perm)
                existing_perms[p_def["code"]] = perm
                created_count += 1

        await session.flush()

        if created_count:
            print(f"✅ Created {created_count} new permissions.")
        else:
            print("✓ All permissions already exist.")

        # 3. Map permissions to roles (clear and re-apply)
        for role_name, role in existing_roles.items():
            codes = ROLE_PERMISSION_MAP.get(role_name, [])
            target_perms = [existing_perms[c] for c in codes if c in existing_perms]

            # Clear existing mappings for this role
            await session.execute(
                delete(role_permissions).where(role_permissions.c.role_id == role.id)
            )

            # Re-add
            role.permissions = target_perms
            print(f"  → {role_name}: {len(target_perms)} permissions")

        await session.flush()
        await session.commit()

    print("\n🎉 Permission seeding complete!")


async def main():
    print("🌱 Seeding permissions...\n")
    try:
        await seed_permissions()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
