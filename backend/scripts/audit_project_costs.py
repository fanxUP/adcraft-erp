"""输出订单项目成本的只读审计报告。

Usage:
    cd backend
    .venv/bin/python scripts/audit_project_costs.py

脚本只执行 SELECT，默认将 JSON 报告输出到 stdout；不会提交事务，也不会
自动修复成本归属或升级数据库结构。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow execution as ``python scripts/audit_project_costs.py`` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_maker, engine  # noqa: E402
from app.services.project_cost_audit_service import (  # noqa: E402
    ProjectCostAuditService,
)


async def main() -> None:
    async with async_session_maker() as db:
        report = await ProjectCostAuditService(db).audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
