"""Seed permissions and role-permission mappings.

Usage:
    cd backend && python scripts/seed_permissions.py

This script reads the DATABASE_URL from the project config,
creates all permission records (idempotent), and maps them
to the built-in roles, including separate resource_manager and
outsource_manager roles.
"""

import asyncio
import sys
from pathlib import Path

# Ensure the backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import engine, async_session_maker
from app.core.permission_catalog import get_permission_definition
from app.models.user import Permission, Role
from sqlalchemy import select


# ── Define all permissions ────────────────────────────────────────────────

ALL_PERMISSIONS: list[dict[str, str | None]] = [
    # System
    {"code": "system:logs", "name": "查看操作日志", "description": "查看系统操作日志"},
    {"code": "system:super_admin", "name": "超级管理员", "description": "管理所有模块、权限和系统安全设置"},
    # Backup
    {"code": "backup:create", "name": "创建备份", "description": "创建数据库备份"},
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
    {"code": "order:change_date", "name": "修改订单下单日期", "description": "在审计和影响预检后修改订单业务下单日期"},
    {"code": "order:view_price", "name": "查看订单价格", "description": "查看订单总额、折扣、税额等订单价格参数"},
    {"code": "order_item:view_price", "name": "查看明细价格", "description": "查看订单明细单价、费用和小计"},
    {"code": "order:task_assign", "name": "分配订单任务可见员工", "description": "为订单指定可见的任务处理员工；不指定时所有任务员工可见"},
    {"code": "catalog:view_price", "name": "查看目录价格", "description": "查看产品、材质和工艺的价格参数"},
    {"code": "finance:view_cost", "name": "查看成本财务", "description": "查看成本、付款、利润和财务金额"},
    {"code": "report:view_financial", "name": "查看财务报表", "description": "查看收款、欠款和经营财务统计"},
    # Task queue and task assignment
    {"code": "task_queue:read", "name": "查看工作台任务", "description": "在工作台查看本人可见的设计、制作、安装任务"},
    {"code": "task_queue:view_all", "name": "查看全部任务", "description": "查看公司所有订单中的设计、制作、安装任务，不改变任务分配"},
    # Design task
    {"code": "design_task:read", "name": "查看设计任务", "description": "查看设计任务列表和详情"},
    {"code": "design_task:list", "name": "查看设计任务列表", "description": "进入设计任务列表页并查询设计任务"},
    {"code": "design_task:assign", "name": "分配设计任务", "description": "维护设计任务负责人"},
    {"code": "design_task:delete", "name": "删除设计任务", "group": "设计任务"},
    {"code": "design_task:create", "name": "创建设计任务", "description": "创建新设计任务"},
    {"code": "design_task:update", "name": "编辑设计任务", "description": "编辑设计任务信息"},
    {"code": "design_task:change_status", "name": "变更设计状态", "description": "变更设计任务状态"},
    # Production task
    {"code": "production_task:read", "name": "查看制作任务", "description": "查看制作任务列表和详情"},
    {"code": "production_task:list", "name": "查看制作任务列表", "description": "进入制作任务列表页并查询制作任务"},
    {"code": "production_task:assign", "name": "分配制作任务", "description": "维护制作任务负责人"},
    {"code": "production_task:delete", "name": "删除制作任务", "group": "制作任务"},
    {"code": "production_task:create", "name": "创建制作任务", "description": "创建新制作任务"},
    {"code": "production_task:update", "name": "编辑制作任务", "description": "编辑制作任务信息"},
    {"code": "production_task:change_status", "name": "变更制作状态", "description": "变更制作任务状态"},
    # Installation task
    {"code": "installation_task:read", "name": "查看安装任务", "description": "查看安装任务列表和详情"},
    {"code": "installation_task:list", "name": "查看安装任务列表", "description": "进入安装任务列表页并查询安装任务"},
    {"code": "installation_task:assign", "name": "分配安装任务", "description": "维护安装任务负责人"},
    {"code": "installation_task:delete", "name": "删除安装任务", "group": "安装任务"},
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
    # Contract
    {"code": "contract:read", "name": "查看合同", "description": "查看合同列表和详情"},
    {"code": "contract:create", "name": "创建合同", "description": "创建新合同"},
    {"code": "contract:update", "name": "编辑合同", "description": "编辑合同信息"},
    {"code": "contract:delete", "name": "删除合同", "description": "删除合同"},
    {"code": "contract:change_status", "name": "变更合同状态", "description": "变更合同状态"},
    # Acceptance
    {"code": "acceptance:read", "name": "查看验收单", "description": "查看验收单列表和详情"},
    {"code": "acceptance:create", "name": "创建验收单", "description": "创建新验收单"},
    {"code": "acceptance:update", "name": "编辑验收单", "description": "编辑验收单及附件"},
    {"code": "acceptance:delete", "name": "删除验收单", "description": "删除草稿验收单"},
    {"code": "acceptance:change_status", "name": "变更验收状态", "description": "提交、通过或驳回验收单"},
    # Expense
    {"code": "expense:read", "name": "查看支出", "description": "查看支出记录"},
    {"code": "expense:create", "name": "创建支出", "description": "创建支出记录"},
    {"code": "expense:update", "name": "编辑支出", "description": "编辑支出信息"},
    {"code": "expense:delete", "name": "删除支出", "description": "删除支出"},
    # Supplier master data
    {"code": "supplier_center:read", "name": "进入供应商中心", "description": "进入统一供应商主数据模块"},
    {"code": "supplier:read", "name": "查看供应商", "description": "查看统一供应商档案"},
    {"code": "supplier:create", "name": "创建供应商", "description": "新增供应商档案"},
    {"code": "supplier:update", "name": "编辑供应商", "description": "编辑供应商档案和启用状态"},
    {"code": "supplier:ledger:read", "name": "查看供应商账务", "description": "查看供应商关联成本、支出和应付统计"},
    {"code": "supplier:bank:view", "name": "查看供应商银行信息", "description": "查看供应商开户行和银行账号"},
    {"code": "supplier:bank:edit", "name": "编辑供应商银行信息", "description": "维护供应商开户行和银行账号"},
    # Chat
    {"code": "chat:read", "name": "查看会话", "description": "查看会话和消息"},
    {"code": "chat:create", "name": "发送消息", "description": "创建会话和发送消息"},
    {"code": "chat:delete", "name": "删除消息", "description": "删除本人消息"},
    {"code": "chat:group:create", "name": "创建群聊", "description": "创建群聊"},
    {"code": "chat:group:manage", "name": "管理群聊", "description": "管理群聊成员和设置"},
    # Resource center / Inventory
    {"code": "resource_center:read", "name": "进入资源中心", "description": "进入公司车辆和高空作业车资源中心"},
    {"code": "inventory:read", "name": "查看库存", "description": "查看库存物料"},
    {"code": "inventory:create", "name": "创建物料", "description": "创建新物料"},
    {"code": "inventory:update", "name": "编辑物料", "description": "编辑物料信息"},
    {"code": "inventory:stock_in", "name": "入库", "description": "物料入库操作"},
    {"code": "inventory:stock_out", "name": "出库", "description": "物料出库操作"},
    # Outsource center
    {"code": "outsource_center:read", "name": "进入外协中心", "description": "进入外协商和外协任务模块"},
    {"code": "outsource_vendor:read", "name": "查看外协商", "description": "查看外协商目录和详情"},
    {"code": "outsource_vendor:create", "name": "创建外协商", "description": "新增外协商"},
    {"code": "outsource_vendor:update", "name": "编辑外协商", "description": "编辑外协商资料"},
    {"code": "outsource_vendor:delete", "name": "删除外协商", "description": "删除外协商资料"},
    {"code": "outsource_task:read", "name": "查看外协任务", "description": "查看外协任务、状态和任务关联明细"},
    {"code": "outsource_task:create", "name": "创建外协任务", "description": "新建外协任务或发送订单明细外协"},
    {"code": "outsource_task:update", "name": "编辑外协任务", "description": "编辑外协任务信息"},
    {"code": "outsource_task:change_status", "name": "变更外协任务状态", "description": "取消、退回等外协任务状态操作"},
    {"code": "outsource_task:delete", "name": "删除外协任务", "description": "删除外协任务并管理回收站"},
    {"code": "outsource_payment:read", "name": "查看外协付款", "description": "查看外协付款记录和任务付款摘要"},
    {"code": "outsource_payment:create", "name": "登记外协付款", "description": "登记外协任务付款"},
    # Report
    {"code": "dashboard:read", "name": "查看经营驾驶舱", "description": "查看公司运营数据驾驶舱"},
    {"code": "report:read", "name": "查看报表", "description": "查看销售报表"},
    # Delivery completion metrics
    {"code": "task_completion:read", "name": "查看个人完成统计", "description": "查看本人完成的项目和订单明细统计"},
    {"code": "task_completion:view_all", "name": "查看全员完成统计", "description": "查看组织总计、员工分组和指定员工完成明细"},
    # Vehicle
    {"code": "vehicle:read", "name": "查看车辆", "description": "查看车辆和司机档案"},
    {"code": "vehicle:create", "name": "创建车辆", "description": "新增车辆和司机"},
    {"code": "vehicle:update", "name": "编辑车辆", "description": "编辑车辆和司机信息、停用/启用/报废"},
    {"code": "vehicle:delete", "name": "删除车辆", "description": "删除车辆和司机（软删除）"},
    {"code": "finance:review", "name": "财务审核", "description": "审核油费、维修保养等车辆费用"},
    # Aerial work platform (高空作业车台账)
    {"code": "aerial:read", "name": "查看高空车台账", "description": "查看高空作业车档案、台账、驾驶员、费用等信息"},
    {"code": "aerial:create", "name": "创建高空车台账", "description": "创建高空车台账记录、驾驶员、费用、安全检查等"},
    {"code": "aerial:update", "name": "编辑高空车台账", "description": "编辑高空车台账记录"},
    {"code": "aerial:delete", "name": "删除高空车台账", "description": "删除台账或附件"},
    {"code": "aerial:finance", "name": "高空车财务操作", "description": "报销驾驶员垫付费用、发放工资"},
    {"code": "aerial:wage", "name": "管理高空车工资", "description": "创建和管理驾驶员工资记录"},
    # AI Features
    {"code": "ai_quote:read", "name": "AI报价助手", "description": "使用AI智能报价功能"},
    {"code": "ai_anomaly:read", "name": "智能异常提醒", "description": "查看AI异常检测结果"},
    {"code": "ai_knowledge:read", "name": "报价知识库", "description": "使用AI报价知识库"},
    {"code": "ai_report:read", "name": "智能经营报告", "description": "查看AI生成的经营报告"},
    # CDR 智能报价
    {"code": "cdr_quote:read", "name": "查看智能报价", "description": "查看CDR智能报价列表和详情"},
    {"code": "cdr_quote:create", "name": "创建智能报价", "description": "创建CDR智能报价和版本"},
    {"code": "cdr_quote:update", "name": "编辑智能报价", "description": "编辑CDR智能报价信息"},
    {"code": "cdr_quote:delete", "name": "删除智能报价", "description": "删除CDR智能报价"},
    {"code": "cdr_quote:view_cost", "name": "查看报价成本", "description": "查看智能报价的预估成本"},
    {"code": "cdr_quote:view_profit", "name": "查看报价利润", "description": "查看智能报价的预估毛利"},
    {"code": "cdr_quote:adjust_price", "name": "调整报价价格", "description": "手工调整智能报价的单价/金额"},
    {"code": "cdr_quote:approve", "name": "审批报价", "description": "审批/驳回智能报价"},
    {"code": "cdr_quote:convert", "name": "转订单", "description": "将智能报价转为销售订单"},
    {"code": "cdr_rule_set:publish", "name": "发布定价规则", "description": "发布定价规则集"},
    {"code": "cdr_device:manage", "name": "管理CDR设备", "description": "管理CorelDRAW插件设备"},
    {"code": "cdr_customer_agreement:manage", "name": "管理客户协议价", "description": "管理客户专项价格协议"},
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
        "contract:read", "contract:create", "contract:update", "contract:delete", "contract:change_status",
        "order:read", "order:create", "order:update", "order:change_status",
        "order:view_price", "order_item:view_price", "catalog:view_price",
        "order:change_date",
        "acceptance:read", "acceptance:create", "acceptance:update", "acceptance:delete", "acceptance:change_status",
        "task_queue:read",
        "design_task:read", "design_task:list", "design_task:assign",
        "production_task:read", "production_task:list", "production_task:assign",
        "installation_task:read", "installation_task:list", "installation_task:assign",
        "order:task_assign",
        "payment:read", "payment:create",
        "expense:read",
        "report:read", "report:view_financial",
        "resource_center:read",
        "ai_quote:read", "ai_anomaly:read", "ai_knowledge:read", "ai_report:read",
        "vehicle:read",
        "aerial:read",
        "cdr_quote:read", "cdr_quote:create", "cdr_quote:update", "cdr_quote:convert", "cdr_quote:adjust_price",
        "cdr_customer_agreement:manage",
    ],
    "designer": [
        "customer:read",
        "product:read",
        "material:read",
        "process:read",
        "task_queue:read",
        "design_task:read", "design_task:create", "design_task:update", "design_task:change_status",
        "production_task:read",
        "installation_task:read",
        "task_completion:read",
    ],
    "production": [
        "customer:read",
        "product:read",
        "material:read",
        "process:read",
        "task_queue:read",
        "design_task:read",
        "production_task:read", "production_task:create", "production_task:update", "production_task:change_status",
        "installation_task:read",
        "inventory:read", "inventory:create", "inventory:update", "inventory:stock_in", "inventory:stock_out",
        "task_completion:read",
    ],
    "installer": [
        "customer:read",
        "task_queue:read",
        "design_task:read",
        "production_task:read",
        "installation_task:read", "installation_task:create", "installation_task:update", "installation_task:change_status",
        "task_completion:read",
    ],
    "finance": [
        "customer:read",
        "order:read",
        "order:view_price", "order_item:view_price",
        "finance:view_cost", "report:view_financial",
        "payment:read", "payment:create", "payment:void",
        "statement:read", "statement:create", "statement:confirm",
        "expense:read", "expense:create", "expense:update", "expense:delete",
        "supplier_center:read", "supplier:read", "supplier:create", "supplier:update",
        "supplier:ledger:read", "supplier:bank:view", "supplier:bank:edit",
        "outsource_center:read", "outsource_vendor:read", "outsource_task:read",
        "outsource_payment:read", "outsource_payment:create",
        "report:read",
        "resource_center:read",
        "ai_quote:read", "ai_anomaly:read", "ai_knowledge:read", "ai_report:read",
        "vehicle:read", "finance:review",
        "aerial:read", "aerial:finance",
    ],
    "resource_manager": [
        "resource_center:read",
        "vehicle:read", "vehicle:create", "vehicle:update", "vehicle:delete",
        "aerial:read", "aerial:create", "aerial:update", "aerial:delete",
        "aerial:finance", "aerial:wage", "finance:review",
    ],
    "outsource_manager": [
        "supplier_center:read", "supplier:read", "supplier:create", "supplier:update",
        "outsource_center:read",
        "outsource_vendor:read", "outsource_vendor:create", "outsource_vendor:update", "outsource_vendor:delete",
        "outsource_task:read", "outsource_task:create", "outsource_task:update",
        "outsource_task:change_status", "outsource_task:delete",
    ],
    "manager": [
        "dashboard:read",
        "report:read",
        "order:read",
        "task_queue:read",
        "task_queue:view_all",
        "design_task:read",
        "production_task:read",
        "installation_task:read",
        "task_completion:read",
        "task_completion:view_all",
    ],
}

# ── Roles referenced by the init-db.sh script ──────────────────────────────
ROLE_NAMES = ["admin", "sales", "designer", "production", "installer", "finance", "resource_manager", "outsource_manager", "manager"]
PERMISSION_SEED_VERSION = 4


def builtin_role_permission_codes(role_name: str) -> list[str] | None:
    """Return defaults only for built-in roles; preserve custom roles."""
    if role_name not in ROLE_NAMES:
        return None
    return ROLE_PERMISSION_MAP[role_name]


def replace_role_permissions(role: Role, permissions: list[Permission]) -> None:
    """交给 ORM 统一计算关联表差异，避免手工清空后只补回新增权限。"""
    role.permissions = list(permissions)


def merge_role_permissions(role: Role, permissions: list[Permission]) -> int:
    """Add newly declared defaults while preserving existing custom grants."""
    existing = list(getattr(role, "permissions", ()) or ())
    existing_codes = {permission.code for permission in existing}
    additions = [permission for permission in permissions if permission.code not in existing_codes]
    if additions:
        role.permissions = [*existing, *additions]
    return len(additions)


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
        for index, p_def in enumerate(ALL_PERMISSIONS):
            definition = get_permission_definition(p_def["code"])
            perm = existing_perms.get(p_def["code"])
            if perm is None:
                perm = Permission(
                    code=p_def["code"],
                    name=p_def["name"],
                    description=p_def.get("description"),
                )
                session.add(perm)
                existing_perms[p_def["code"]] = perm
                created_count += 1

            # Keep labels backward-compatible while making the semantic
            # catalog queryable by the admin UI and authorization services.
            perm.name = p_def["name"]
            perm.description = p_def.get("description")
            perm.module = definition.module
            perm.resource = definition.resource
            perm.action = definition.action
            perm.kind = definition.kind
            perm.sensitivity = definition.sensitivity
            perm.status = "active"
            perm.sort_order = index

        await session.flush()

        if created_count:
            print(f"✅ Created {created_count} new permissions.")
        else:
            print("✓ All permissions already exist.")

        # 3. Apply built-in defaults by version.  Existing role associations
        # are intentionally preserved so a deployment cannot erase a custom
        # combination; a new seed version only adds newly declared defaults.
        for role_name, role in existing_roles.items():
            codes = builtin_role_permission_codes(role_name) or []
            if getattr(role, "permission_seed_version", 0) < PERMISSION_SEED_VERSION:
                target_perms = [existing_perms[c] for c in codes if c in existing_perms]
                added_count = merge_role_permissions(role, target_perms)
                role.permission_seed_version = PERMISSION_SEED_VERSION
                print(f"  → {role_name}: added {added_count} default permissions; preserved existing grants")
            else:
                print(f"  ↷ {role_name}: existing permission combination preserved ({len(role.permissions)} permissions)")

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
