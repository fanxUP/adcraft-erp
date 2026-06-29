"""Rule-based anomaly detector — scans database for 6 categories of anomalies.

Zero dependencies beyond the existing SQLAlchemy models.
Works without any AI API key.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.quote import Quote, QuoteItem
from app.models.customer import Customer
from app.models.task import InstallationTask
from app.models.outsource import OutsourceTask
from app.models.inventory import InventoryItem
from app.models.product import Product, Material

# Terminal states — orders in these states are considered "closed"
ORDER_TERMINAL_STATES = {"completed", "delivered", "cancelled", "returned"}

# Terminal states for outsource tasks
OUTSOURCE_TERMINAL_STATES = {"completed", "settled"}

# Terminal states for installation tasks
INSTALLATION_TERMINAL_STATES = {"completed", "cancelled"}


class AnomalyDetector:
    """Scans the database for business anomalies and returns alert dicts.

    Usage:
        detector = AnomalyDetector(db)
        results = await detector.scan_all()
        # results dict: alerts (list), summary (critical/warning/info counts)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def scan_all(self) -> dict:
        """Run all 6 scans and return aggregated results."""
        now = datetime.now(timezone.utc)
        results = await asyncio_gather_fallback(
            self._scan_underpriced_quotes(),
            self._scan_overdue_orders(now),
            self._scan_unpaid_installations(),
            self._scan_credit_exceeded(now),
            self._scan_outsource_delays(now),
            self._scan_inventory_shortages(),
        )

        alerts: list[dict] = []
        for group in results:
            alerts.extend(group)

        severity_counts = {"critical": 0, "warning": 0, "info": 0}
        for alert in alerts:
            severity_counts[alert["severity"]] = severity_counts.get(alert["severity"], 0) + 1

        return {
            "alerts": alerts,
            "summary": severity_counts,
        }

    # ── Rule 1: Quote Underpriced ───────────────────────────────────────

    async def _scan_underpriced_quotes(self) -> list[dict]:
        """Find confirmed quotes where total is potentially below material cost.

        Estimates cost as: sum(item.unit_price * item.length * item.width * item.quantity)
        Flags if total_amount < estimated_cost (meaning possible underpricing).
        """
        alerts: list[dict] = []

        result = await self.db.execute(
            select(Quote).where(
                Quote.status.in_(["confirmed"]),
                Quote.deleted_at.is_(None),
            )
        )
        quotes = result.scalars().all()

        for quote in quotes:
            if not quote.items:
                continue
            estimated_cost = 0.0
            for item in quote.items:
                area = (item.length or 0) * (item.width or 0) * (item.quantity or 1)
                estimated_cost += area * (item.unit_price or 0)

            if estimated_cost > 0 and float(quote.total_amount) < estimated_cost:
                gap = estimated_cost - float(quote.total_amount)
                alerts.append({
                    "type": "quote_underpriced",
                    "severity": "warning",
                    "object_type": "quote",
                    "object_id": str(quote.id),
                    "title": f"报价 {quote.quote_no} 可能低于成本",
                    "detail": f"总价 ¥{float(quote.total_amount):,.2f}，估算成本 ¥{estimated_cost:,.2f}，差距 ¥{gap:,.2f}（{gap / estimated_cost * 100:.1f}%）",
                    "created_at": quote.created_at.isoformat() if quote.created_at else "",
                })

        return alerts

    # ── Rule 2: Overdue Orders ─────────────────────────────────────────

    async def _scan_overdue_orders(self, now: datetime) -> list[dict]:
        """Find non-terminal orders past their delivery deadline."""
        alerts: list[dict] = []

        result = await self.db.execute(
            select(Order).where(
                Order.status.notin_(ORDER_TERMINAL_STATES),
                Order.delivery_deadline.isnot(None),
                Order.delivery_deadline < now,
                Order.deleted_at.is_(None),
            )
        )
        orders = result.scalars().all()

        for order in orders:
            deadline = order.delivery_deadline
            days_overdue = 0
            if deadline:
                days_overdue = (now - deadline).days

            severity = "critical" if days_overdue > 14 else ("warning" if days_overdue > 3 else "info")
            alerts.append({
                "type": "order_overdue",
                "severity": severity,
                "object_type": "order",
                "object_id": str(order.id),
                "title": f"订单 {order.order_no} 已逾期 {days_overdue} 天",
                "detail": f"项目「{order.project_name}」，状态「{order.status}」，交付截止 {deadline.strftime('%Y-%m-%d') if deadline else '未知'}",
                "created_at": now.isoformat(),
            })

        return alerts

    # ── Rule 3: Install Completed but Unpaid ────────────────────────────

    async def _scan_unpaid_installations(self) -> list[dict]:
        """Find orders where installation is complete but payment is not fully collected."""
        alerts: list[dict] = []

        result = await self.db.execute(
            select(InstallationTask).where(
                InstallationTask.status.in_(INSTALLATION_TERMINAL_STATES),
            )
        )
        install_tasks = result.scalars().all()

        for task in install_tasks:
            order_result = await self.db.execute(
                select(Order).where(
                    Order.id == task.order_id,
                    Order.unpaid_amount > 0,
                    Order.deleted_at.is_(None),
                )
            )
            order = order_result.scalar_one_or_none()
            if order and float(order.unpaid_amount) > 0:
                alerts.append({
                    "type": "install_unpaid",
                    "severity": "warning",
                    "object_type": "order",
                    "object_id": str(order.id),
                    "title": f"安装完成但未收款 — 订单 {order.order_no}",
                    "detail": f"项目「{order.project_name}」安装已完成，但仍未收款 ¥{float(order.unpaid_amount):,.2f}",
                    "created_at": task.completed_at.isoformat() if task.completed_at else "",
                })

        return alerts

    # ── Rule 4: Customer Credit Exceeded ────────────────────────────────

    async def _scan_credit_exceeded(self, now: datetime) -> list[dict]:
        """Find orders where unpaid exceeds the customer's allowed payment days."""
        alerts: list[dict] = []

        result = await self.db.execute(
            select(Order).where(
                Order.unpaid_amount > 0,
                Order.deleted_at.is_(None),
            )
        )
        orders = result.scalars().all()

        for order in orders:
            if not order.created_at or float(order.unpaid_amount) <= 0:
                continue

            customer_result = await self.db.execute(
                select(Customer).where(
                    Customer.id == order.customer_id,
                    Customer.deleted_at.is_(None),
                )
            )
            customer = customer_result.scalar_one_or_none()
            if not customer or customer.default_payment_days <= 0:
                continue

            days_since = (now - order.created_at).days
            if days_since > customer.default_payment_days:
                days_past = days_since - customer.default_payment_days
                alerts.append({
                    "type": "customer_credit_exceeded",
                    "severity": "critical" if days_past > 30 else "warning",
                    "object_type": "order",
                    "object_id": str(order.id),
                    "title": f"客户「{customer.name}」欠款超账期",
                    "detail": f"订单 {order.order_no} 欠款 ¥{float(order.unpaid_amount):,.2f}，已超出账期 {days_past} 天（账期 {customer.default_payment_days} 天）",
                    "created_at": now.isoformat(),
                })

        return alerts

    # ── Rule 5: Outsource Delays ───────────────────────────────────────

    async def _scan_outsource_delays(self, now: datetime) -> list[dict]:
        """Find outsource tasks past expected return date but not completed."""
        alerts: list[dict] = []

        result = await self.db.execute(
            select(OutsourceTask).where(
                OutsourceTask.status.notin_(OUTSOURCE_TERMINAL_STATES),
                OutsourceTask.expected_at.isnot(None),
                OutsourceTask.expected_at < now,
            )
        )
        tasks = result.scalars().all()

        for task in tasks:
            expected = task.expected_at
            days_delayed = 0
            if expected:
                days_delayed = (now - expected).days

            severity = "critical" if days_delayed > 7 else "warning"
            alerts.append({
                "type": "outsource_delayed",
                "severity": severity,
                "object_type": "outsource_task",
                "object_id": str(task.id),
                "title": f"外协任务 {task.task_no} 已延迟 {days_delayed} 天",
                "detail": f"外协商「{task.vendor.name if task.vendor else '未知'}」，任务类型 {task.task_type}，预计回货 {expected.strftime('%Y-%m-%d') if expected else '未知'}，当前状态「{task.status}」",
                "created_at": now.isoformat(),
            })

        return alerts

    # ── Rule 6: Inventory Low ──────────────────────────────────────────

    async def _scan_inventory_shortages(self) -> list[dict]:
        """Find inventory items at or below safety stock level."""
        alerts: list[dict] = []

        result = await self.db.execute(
            select(InventoryItem).where(
                InventoryItem.quantity <= InventoryItem.min_quantity,
            )
        )
        items = result.scalars().all()

        for item in items:
            if float(item.quantity) <= 0:
                severity = "critical"
                title = f"库存耗尽 — {item.material_name}"
                detail = f"物料「{item.material_name}」库存为 {float(item.quantity):g}{item.material_unit or ''}，安全库存 {float(item.min_quantity):g}"
            else:
                severity = "warning"
                title = f"库存不足 — {item.material_name}"
                detail = f"物料「{item.material_name}」库存 {float(item.quantity):g}{item.material_unit or ''}，低于安全线 {float(item.min_quantity):g}"

            alerts.append({
                "type": "inventory_low",
                "severity": severity,
                "object_type": "inventory_item",
                "object_id": str(item.id),
                "title": title,
                "detail": detail,
                "created_at": item.created_at.isoformat() if item.created_at else "",
            })

        return alerts


# ── Helper: async gather fallback for Python 3.12+ ─────────────────────

async def asyncio_gather_fallback(*coros):
    """Gather coroutines — works with any asyncio version."""
    import asyncio
    return await asyncio.gather(*coros)
