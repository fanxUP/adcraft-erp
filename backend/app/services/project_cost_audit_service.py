"""只读审计订单项目成本的归属和财务汇总。

该服务只执行 SELECT，不负责修复、回填、删除或迁移数据。它刻意使用
SQL 文本而不是完整 ORM 查询，以便在本地数据库尚未升级到最新结构时，
仍能输出“缺少哪些列、哪些检查无法完成”的证据。
"""

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


MONEY_QUANTUM = Decimal("0.01")

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "business_documents": {
        "id",
        "doc_type",
        "total_amount",
        "cost_amount",
        "gross_profit",
        "deleted_at",
    },
    "business_document_items": {"id", "document_id"},
    "project_costs": {
        "id",
        "cost_no",
        "document_id",
        "document_item_id",
        "amount",
        "deleted_at",
    },
    "outsource_tasks": {
        "related_doc_id",
        "related_doc_type",
        "status",
        "total_amount",
        "deleted_at",
    },
    "stock_records": {"document_id", "record_type", "total_cost"},
}

CURRENT_ITEM_COLUMNS = {"lifecycle_status"}


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _money(value: Any) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def classify_cost_reference(reference: Mapping[str, Any]) -> list[str]:
    """Return stable issue codes for one active project-cost reference."""

    issues: list[str] = []
    document_id = reference.get("document_id")
    if not document_id or not reference.get("document_exists"):
        issues.append("document_missing")

    item_id = reference.get("item_id")
    if not item_id:
        return issues

    if not reference.get("item_exists"):
        issues.append("item_missing")
        return issues

    if reference.get("item_document_id") != document_id:
        issues.append("item_cross_document")
        return issues

    if reference.get("lifecycle_status_available") and reference.get(
        "item_lifecycle_status"
    ) not in (None, "active"):
        issues.append("item_inactive")
    return issues


def build_financial_check(row: Mapping[str, Any]) -> dict[str, Any]:
    """Compare stored order totals with the three independent cost sources."""

    total_amount = _money(row.get("total_amount"))
    stored_cost = _money(row.get("stored_cost"))
    stored_profit = _money(row.get("stored_profit"))
    outsource_cost = _money(row.get("outsource_cost"))
    inventory_cost = _money(row.get("inventory_cost"))
    manual_cost = _money(row.get("manual_cost"))
    expected_cost = _money(outsource_cost + inventory_cost + manual_cost)
    expected_profit = _money(total_amount - expected_cost)

    return {
        "order_id": row.get("order_id"),
        "order_no": row.get("order_no"),
        "total_amount": total_amount,
        "stored_cost": stored_cost,
        "stored_profit": stored_profit,
        "outsource_cost": outsource_cost,
        "inventory_cost": inventory_cost,
        "manual_cost": manual_cost,
        "expected_cost": expected_cost,
        "expected_profit": expected_profit,
        "cost_matches": stored_cost == expected_cost,
        "profit_matches": stored_profit == expected_profit,
        "manual_record_count": int(row.get("manual_record_count") or 0),
        "manual_order_scope_count": int(row.get("manual_order_scope_count") or 0),
        "manual_item_scope_count": int(row.get("manual_item_scope_count") or 0),
        "outsource_record_count": int(row.get("outsource_record_count") or 0),
        "inventory_record_count": int(row.get("inventory_record_count") or 0),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


class ProjectCostAuditService:
    """Run a read-only audit against the current database connection."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _schema_columns(self) -> dict[str, set[str]]:
        result = await self.db.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                """
            )
        )
        columns: dict[str, set[str]] = {}
        for row in result.mappings().all():
            columns.setdefault(row["table_name"], set()).add(row["column_name"])
        return columns

    @staticmethod
    def _schema_report(columns: dict[str, set[str]]) -> dict[str, Any]:
        missing_required = {
            table: sorted(required - columns.get(table, set()))
            for table, required in REQUIRED_COLUMNS.items()
            if required - columns.get(table, set())
        }
        missing_current = {
            "business_document_items": sorted(
                CURRENT_ITEM_COLUMNS
                - columns.get("business_document_items", set())
            )
        }
        if not missing_current["business_document_items"]:
            missing_current = {}

        warnings = []
        if missing_current:
            warnings.append(
                "订单明细生命周期字段缺失，无法完成已作废/已替代明细引用审计"
            )
        if missing_required:
            warnings.append("成本或订单汇总所需的基础字段缺失，相关检查被跳过")
        return {
            "ready": not missing_required and not missing_current,
            "missing_required_columns": missing_required,
            "missing_current_columns": missing_current,
            "warnings": warnings,
        }

    async def _cost_references(self, lifecycle_available: bool) -> list[dict[str, Any]]:
        lifecycle_expression = (
            "bi.lifecycle_status" if lifecycle_available else "NULL::text"
        )
        result = await self.db.execute(
            text(
                f"""
                SELECT
                    pc.id::text AS record_id,
                    pc.cost_no,
                    pc.document_id::text AS document_id,
                    (bd.id IS NOT NULL) AS document_exists,
                    bd.doc_type AS document_type,
                    pc.document_item_id::text AS item_id,
                    (bi.id IS NOT NULL) AS item_exists,
                    bi.document_id::text AS item_document_id,
                    {lifecycle_expression} AS item_lifecycle_status,
                    pc.amount
                FROM project_costs pc
                LEFT JOIN business_documents bd ON bd.id = pc.document_id
                LEFT JOIN business_document_items bi ON bi.id = pc.document_item_id
                WHERE pc.deleted_at IS NULL
                ORDER BY pc.created_at NULLS LAST, pc.cost_no
                """
            )
        )
        return [
            {
                **dict(row),
                "lifecycle_status_available": lifecycle_available,
            }
            for row in result.mappings().all()
        ]

    async def _financial_rows(self) -> list[dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                WITH outsource AS (
                    SELECT
                        related_doc_id AS document_id,
                        COALESCE(SUM(total_amount), 0) AS outsource_cost,
                        COUNT(*) AS outsource_record_count
                    FROM outsource_tasks
                    WHERE deleted_at IS NULL
                      AND related_doc_type = 'order'
                      AND status IN ('completed', 'settled')
                    GROUP BY related_doc_id
                ), inventory AS (
                    SELECT
                        document_id,
                        COALESCE(SUM(total_cost), 0) AS inventory_cost,
                        COUNT(*) AS inventory_record_count
                    FROM stock_records
                    WHERE record_type = 'out'
                    GROUP BY document_id
                ), manual AS (
                    SELECT
                        document_id,
                        COALESCE(SUM(amount), 0) AS manual_cost,
                        COUNT(*) AS manual_record_count,
                        COUNT(*) FILTER (WHERE document_item_id IS NULL)
                            AS manual_order_scope_count,
                        COUNT(*) FILTER (WHERE document_item_id IS NOT NULL)
                            AS manual_item_scope_count
                    FROM project_costs
                    WHERE deleted_at IS NULL
                    GROUP BY document_id
                )
                SELECT
                    bd.id::text AS order_id,
                    bd.doc_no AS order_no,
                    bd.total_amount,
                    bd.cost_amount AS stored_cost,
                    bd.gross_profit AS stored_profit,
                    COALESCE(outsource.outsource_cost, 0) AS outsource_cost,
                    COALESCE(inventory.inventory_cost, 0) AS inventory_cost,
                    COALESCE(manual.manual_cost, 0) AS manual_cost,
                    COALESCE(manual.manual_record_count, 0) AS manual_record_count,
                    COALESCE(manual.manual_order_scope_count, 0)
                        AS manual_order_scope_count,
                    COALESCE(manual.manual_item_scope_count, 0)
                        AS manual_item_scope_count,
                    COALESCE(outsource.outsource_record_count, 0)
                        AS outsource_record_count,
                    COALESCE(inventory.inventory_record_count, 0)
                        AS inventory_record_count
                FROM business_documents bd
                LEFT JOIN outsource ON outsource.document_id = bd.id
                LEFT JOIN inventory ON inventory.document_id = bd.id
                LEFT JOIN manual ON manual.document_id = bd.id
                WHERE bd.doc_type = 'order'
                  AND bd.deleted_at IS NULL
                ORDER BY bd.created_at NULLS LAST, bd.doc_no
                """
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def audit(self) -> dict[str, Any]:
        columns = await self._schema_columns()
        schema = self._schema_report(columns)
        missing_required = schema["missing_required_columns"]
        lifecycle_available = not schema["missing_current_columns"]

        references: list[dict[str, Any]] = []
        if not missing_required.get("project_costs") and not missing_required.get(
            "business_documents"
        ) and not missing_required.get("business_document_items"):
            references = await self._cost_references(lifecycle_available)

        issue_counts: Counter[str] = Counter()
        issue_records = []
        for reference in references:
            issues = classify_cost_reference(reference)
            if not issues:
                continue
            issue_counts.update(issues)
            issue_records.append(
                {
                    "record_id": reference.get("record_id"),
                    "cost_no": reference.get("cost_no"),
                    "document_id": reference.get("document_id"),
                    "item_id": reference.get("item_id"),
                    "issues": issues,
                }
            )

        cost_scope_status = "PASS"
        if missing_required or not lifecycle_available:
            cost_scope_status = "BLOCKED"
        elif issue_records:
            cost_scope_status = "ATTENTION"

        financial_rows: list[dict[str, Any]] = []
        if not missing_required:
            financial_rows = await self._financial_rows()
        financial_checks = [build_financial_check(row) for row in financial_rows]
        financial_mismatches = [
            row
            for row in financial_checks
            if not row["cost_matches"] or not row["profit_matches"]
        ]
        financial_status = "PASS" if not missing_required and not financial_mismatches else "ATTENTION"
        if missing_required:
            financial_status = "BLOCKED"

        return _json_safe(
            {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "read_only": True,
                "schema": schema,
                "cost_scope": {
                    "status": cost_scope_status,
                    "active_record_count": len(references),
                    "issue_record_count": len(issue_records),
                    "issue_counts": dict(issue_counts),
                    "issues": issue_records,
                },
                "financials": {
                    "status": financial_status,
                    "orders_checked": len(financial_checks),
                    "mismatch_count": len(financial_mismatches),
                    "orders": financial_checks,
                    "source_partition": {
                        "status": "PASS" if not missing_required else "BLOCKED",
                        "rule": "自动成本按完成/结算外协、库存出库、未删除手工项目成本三类独立汇总，每条来源记录只进入对应来源一次",
                    },
                    "manual_overlap": {
                        "status": "UNVERIFIABLE",
                        "reason": "当前 project_costs 没有外协任务或库存出库记录的来源ID，无法仅凭数据库判断人工登记是否重复录入同一笔自动成本",
                    },
                },
            }
        )
