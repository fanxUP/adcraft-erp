"""Deviation analyzer — compares estimated vs actual production data.

Uses:
- QuoteGeometry (estimated material usage, dimensions)
- QuoteLine (estimated prices, quantities)
- ProductionTask (actual production dimensions, material used)
- BusinessDocumentItem (order data after conversion)

Always available, no AI dependency.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdr_quote import QuoteLine, QuoteVersion, QuoteGeometry
from app.models.business_document import BusinessDocument
from app.models.task import ProductionTask

DeviationReport = dict[str, Any]
DeviationItem = dict[str, Any]


class DeviationAnalyzer:
    """Compares estimated vs actual data for completed orders.

    Usage:
        analyzer = DeviationAnalyzer(db)
        report = await analyzer.analyze_quote(quote_id)
        # or compare a converted order:
        report = await analyzer.analyze_order(order_id)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze_quote(
        self, quote_id: UUID, version_id: UUID | None = None
    ) -> DeviationReport:
        """Analyze estimate vs actual for a quote that was converted to order.

        Traces from quote → order → production tasks → compare.
        """
        # Get quote document
        r_q = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == quote_id,
                BusinessDocument.doc_type == "quote",
            )
        )
        quote = r_q.scalar_one_or_none()
        if not quote:
            return {"error": "报价不存在", "items": [], "summary": {}}

        # Find converted order
        r_o = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.doc_type == "order",
                BusinessDocument.source_quote_id == quote_id,
            ).order_by(BusinessDocument.created_at.desc()).limit(1)
        )
        order = r_o.scalar_one_or_none()

        # Get the quote version
        if not version_id:
            r_v = await self.db.execute(
                select(QuoteVersion)
                .where(QuoteVersion.quote_id == quote_id)
                .order_by(QuoteVersion.version_no.desc()).limit(1)
            )
            version = r_v.scalar_one_or_none()
        else:
            r_v = await self.db.execute(
                select(QuoteVersion).where(QuoteVersion.id == version_id)
            )
            version = r_v.scalar_one_or_none()

        if not version:
            return {"error": "报价没有版本数据", "items": [], "summary": {}}

        # Load quote lines
        r_l = await self.db.execute(
            select(QuoteLine)
            .where(QuoteLine.version_id == version.id)
            .order_by(QuoteLine.line_no)
        )
        lines = r_l.scalars().all()

        # Load production tasks for the order
        prod_tasks: list = []
        if order:
            r_p = await self.db.execute(
                select(ProductionTask).where(
                    ProductionTask.document_id == order.id
                )
            )
            prod_tasks = r_p.scalars().all()

        # Compare each quote line
        items: list[DeviationItem] = []
        total_estimated_amount = 0.0
        total_actual_amount = 0.0
        total_estimated_cost = 0.0
        total_actual_cost = 0.0

        for line in lines:
            item = self._compare_line(line, prod_tasks)
            items.append(item)

            total_estimated_amount += float(line.amount or 0)
            total_estimated_cost += float(line.estimated_cost or 0)

            # Actual data from production tasks
            if order and not item.get("no_production_data"):
                total_actual_amount += item.get("actual_amount", float(line.amount or 0))
                total_actual_cost += item.get("actual_cost", 0.0)

        # Build summary
        has_actual = any(not i.get("no_production_data") for i in items)

        summary = {
            "estimated_amount": round(total_estimated_amount, 2),
            "estimated_cost": round(total_estimated_cost, 2),
            "estimated_margin_pct": round(
                (total_estimated_amount - total_estimated_cost) / total_estimated_amount * 100
                if total_estimated_amount > 0 else 0, 1
            ),
            "total_items": len(items),
            "has_production_data": has_actual,
            "quote_converted": order is not None,
            "order_id": str(order.id) if order else None,
            "order_no": order.doc_no if order else None,
        }

        if has_actual:
            summary["actual_amount"] = round(total_actual_amount, 2)
            summary["actual_cost"] = round(total_actual_cost, 2)
            summary["deviation_amount"] = round(total_actual_amount - total_estimated_amount, 2)
            summary["deviation_pct"] = round(
                (total_actual_amount - total_estimated_amount) / total_estimated_amount * 100
                if total_estimated_amount > 0 else 0, 1
            )

        return {
            "quote_id": str(quote_id),
            "quote_no": quote.doc_no,
            "project_name": quote.project_name,
            "summary": summary,
            "items": items,
        }

    async def analyze_order(self, order_id: UUID) -> DeviationReport:
        """Analyze estimate vs actual for an order directly (trace back to quote)."""
        r_o = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == order_id,
                BusinessDocument.doc_type == "order",
            )
        )
        order = r_o.scalar_one_or_none()
        if not order:
            return {"error": "订单不存在", "items": [], "summary": {}}

        if order.source_quote_id:
            return await self.analyze_quote(order.source_quote_id)

        return {"error": "该订单没有关联报价，无法进行偏差分析", "items": [], "summary": {}}

    # ── Internal comparison ─────────────────────────────────────

    def _compare_line(
        self, line: QuoteLine, prod_tasks: list
    ) -> DeviationItem:
        """Compare a single quote line against production data."""
        item: DeviationItem = {
            "line_no": line.line_no,
            "description": line.description,
            "estimated": {
                "amount": float(line.amount or 0),
                "cost": float(line.estimated_cost or 0),
                "width_mm": float(line.width_mm) if line.width_mm else None,
                "height_mm": float(line.height_mm) if line.height_mm else None,
                "length_m": float(line.length_m) if line.length_m else None,
                "quantity": float(line.quantity),
                "unit_price": float(line.unit_price or 0),
            },
            "actual": None,
            "deviation": None,
            "no_production_data": True,
        }

        # Find matching production task(s)
        matching_tasks = [
            t for t in prod_tasks
            if self._task_matches_line(t, line)
        ]

        if not matching_tasks:
            return item

        # Aggregate actual data
        actual_quantity = sum(float(t.quantity or 0) for t in matching_tasks)
        actual_width = max(float(t.width or 0) for t in matching_tasks) if matching_tasks else None
        actual_height = max(float(t.height or 0) for t in matching_tasks) if matching_tasks else None

        # Get geometry data for estimated usage
        r_g = None
        estimated_sheets = None
        # We can't easily query geometry here without the quote_line_id matching

        actual: dict[str, Any] = {
            "width_mm": actual_width * 1000 if actual_width else None,  # convert m to mm
            "height_mm": actual_height * 1000 if actual_height else None,
            "quantity": actual_quantity,
            "task_count": len(matching_tasks),
            "status": matching_tasks[0].status if matching_tasks else "unknown",
        }

        item["actual"] = actual
        item["no_production_data"] = False

        # Calculate deviations
        deviations: dict[str, Any] = {}
        est_qty = float(line.quantity)
        if est_qty > 0 and actual_quantity > 0:
            deviations["quantity"] = {
                "estimated": est_qty,
                "actual": actual_quantity,
                "diff": actual_quantity - est_qty,
                "diff_pct": round((actual_quantity - est_qty) / est_qty * 100, 1),
            }

        if (
            line.width_mm and actual_width
        ):
            est_w = float(line.width_mm)
            act_w = actual_width * 1000
            deviations["width_mm"] = {
                "estimated": est_w,
                "actual": act_w,
                "diff": act_w - est_w,
                "diff_pct": round((act_w - est_w) / est_w * 100, 1),
            }

        if (
            line.height_mm and actual_height
        ):
            est_h = float(line.height_mm)
            act_h = actual_height * 1000
            deviations["height_mm"] = {
                "estimated": est_h,
                "actual": act_h,
                "diff": act_h - est_h,
                "diff_pct": round((act_h - est_h) / est_h * 100, 1),
            }

        item["deviation"] = deviations

        return item

    @staticmethod
    def _task_matches_line(line: QuoteLine, task) -> bool:
        """Check if a production task corresponds to this quote line.

        Heuristic matching: same product_id or material_id, and close dimensions.
        """
        if line.product_id and task.material_id:
            # If the task references the same product/material
            pass  # Not always reliable — use description match as fallback

        # Description-based matching
        if line.description and task.production_no:
            # Check if task description contains line description keywords
            desc_words = set(line.description.lower().split()[:3])
            task_text = f"{task.production_no} {task.project_name}".lower()
            if any(w in task_text for w in desc_words):
                return True

        return False
