"""Rule-based report composer — template-driven business narrative reports.

Reuses the existing ReportService for statistics and adds narrative generation.
Always available, no AI dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.report_service import ReportService
from app.ai.rule_based.anomaly_detector import AnomalyDetector

# Narrative templates with {placeholder} interpolation
WEEKLY_TEMPLATE = (
    "本周（第{week}周），公司共承接 **{order_count}** 个订单，"
    "订单总额 **¥{order_amount:,.2f}**。\n\n"
    "本周收款 **¥{payment_amount:,.2f}**，其中新增欠款 **¥{new_debt:,.2f}**。\n\n"
    "当前待处理：\n"
    "- 待设计：{pending_design} 个\n"
    "- 待制作：{pending_production} 个\n"
    "- 待安装：{pending_installation} 个\n\n"
    "逾期订单 {overdue_count} 个，需优先处理。\n"
    "{anomaly_section}"
)

MONTHLY_TEMPLATE = (
    "## {year}年{month}月经营报告\n\n"
    "### 一、总体概览\n\n"
    "{year}年{month}月，公司共承接 **{order_count}** 个订单，"
    "订单总额 **¥{order_amount:,.2f}**。\n\n"
    "与上月相比，订单数量增长。\n\n"
    "### 二、收款情况\n\n"
    "本月收款 **¥{payment_amount:,.2f}**，收款率 **{collection_rate:.1%}**。\n"
    "月末未收款 **¥{unpaid_amount:,.2f}**。\n\n"
    "### 三、生产与安装\n\n"
    "- 待设计任务：{pending_design} 个\n"
    "- 待制作任务：{pending_production} 个\n"
    "- 待安装任务：{pending_installation} 个\n"
    "- 逾期订单：{overdue_count} 个\n\n"
    "### 四、状态分布\n\n"
    "{status_breakdown}\n\n"
    "{anomaly_section}"
)


class ReportComposer:
    """Generate structured business narrative reports using templates.

    Usage:
        composer = ReportComposer(db)
        report = await composer.generate_report("monthly", year=2026, month=6)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_service = ReportService(db)

    async def generate_report(
        self,
        period: str = "monthly",
        year: int | None = None,
        month: int | None = None,
        week: int | None = None,
    ) -> dict:
        """Generate a business narrative report.

        Args:
            period: "weekly" or "monthly"
            year: Report year (defaults to current year)
            month: Report month (for monthly, defaults to current month)
            week: ISO week number (for weekly)

        Returns:
            dict with stats, narrative, and suggestions
        """
        now = datetime.now(timezone.utc)
        y = year or now.year

        if period == "monthly":
            m = month or now.month
            report_data = await self.report_service.get_monthly_report(y, m)
            dashboard = await self.report_service.get_dashboard()

            stats = {
                "order_count": report_data["order_count"],
                "order_amount": report_data["order_amount"],
                "payment_count": report_data["payment_count"],
                "payment_amount": report_data["payment_amount"],
                "unpaid_amount": report_data["unpaid_amount"],
                "status_breakdown": report_data.get("status_breakdown", {}),
                "pending_design": dashboard["pending_design_count"],
                "pending_production": dashboard["pending_production_count"],
                "pending_installation": dashboard["pending_installation_count"],
                "overdue_count": dashboard["overdue_order_count"],
                "collection_rate": (
                    report_data["payment_amount"] / report_data["order_amount"]
                    if report_data["order_amount"] > 0
                    else 0
                ),
            }

            # Build status breakdown text
            sb_parts: list[str] = []
            for status, count in stats["status_breakdown"].items():
                sb_parts.append(f"- {status}：{count} 个")
            status_text = "\n".join(sb_parts) if sb_parts else "暂无数据"

            # Anomaly section
            anomaly_text = await self._get_anomaly_section()

            template_vars = {k: v for k, v in stats.items() if k != "status_breakdown"}
            template_vars["year"] = y
            template_vars["month"] = m
            template_vars["status_breakdown"] = status_text
            template_vars["anomaly_section"] = anomaly_text
            narrative = MONTHLY_TEMPLATE.format(**template_vars)

        else:
            # Weekly report
            w = week or now.isocalendar()[1]
            dashboard = await self.report_service.get_dashboard()
            daily = await self.report_service.get_daily_report()

            order_amount = dashboard["month_order_amount"]
            payment_amount = dashboard["month_payment_amount"]
            new_debt = max(0, order_amount - payment_amount)

            stats = {
                "week": w,
                "order_count": daily["order_count"],
                "order_amount": order_amount,
                "payment_amount": payment_amount,
                "new_debt": new_debt,
                "pending_design": dashboard["pending_design_count"],
                "pending_production": dashboard["pending_production_count"],
                "pending_installation": dashboard["pending_installation_count"],
                "overdue_count": dashboard["overdue_order_count"],
            }

            anomaly_text = await self._get_anomaly_section()
            template_vars = dict(stats)
            template_vars["anomaly_section"] = anomaly_text
            narrative = WEEKLY_TEMPLATE.format(**template_vars)

        # Generate suggestions
        suggestions = await self._generate_suggestions(stats)

        return {
            "period": period,
            "year": y,
            "month": month if period == "monthly" else None,
            "week": week if period == "weekly" else None,
            "stats": stats,
            "narrative": narrative,
            "suggestions": suggestions,
        }

    async def _get_anomaly_section(self) -> str:
        try:
            detector = AnomalyDetector(self.db)
            result = await detector.scan_all()
            critical = result["summary"].get("critical", 0)
            warning = result["summary"].get("warning", 0)
            if critical + warning == 0:
                return "### 五、异常提醒\n\n本月未发现严重异常。"
            return (
                f"### 五、异常提醒\n\n"
                f"⚠️ 发现 **{critical}** 项严重异常，**{warning}** 项警告。"
                f"请访问「智能异常提醒」查看详情。\n"
            )
        except Exception:
            return ""

    async def _generate_suggestions(self, stats: dict) -> list[str]:
        suggestions: list[str] = []

        overdue = stats.get("overdue_count", 0)
        if overdue > 0:
            suggestions.append(f"有 {overdue} 个逾期订单需要优先处理，建议联系客户确认交付时间")

        pending_design = stats.get("pending_design", 0)
        if pending_design > 3:
            suggestions.append(f"待设计任务积压 {pending_design} 个，建议协调设计资源或外协")

        collection_rate = stats.get("collection_rate", 0)
        if collection_rate < 0.6:
            suggestions.append(f"本月收款率仅 {collection_rate:.0%}，建议加大催款力度")

        return suggestions
