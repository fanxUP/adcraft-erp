"""Tests for ReportComposer — template-based business report generation."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


class TestReportComposer:
    def test_generate_monthly_report_with_mock(self, mock_db):
        """ReportComposer should generate monthly report with template interpolation."""
        from app.ai.rule_based.report_composer import ReportComposer

        composer = ReportComposer(mock_db)
        # Mock the report_service methods
        composer.report_service.get_monthly_report = _async_return({
            "year": 2026, "month": 6,
            "order_count": 10, "order_amount": 100000.0,
            "payment_count": 8, "payment_amount": 80000.0,
            "unpaid_amount": 20000.0,
            "status_breakdown": {"confirmed": 5, "completed": 5},
            "orders": [],
        })
        composer.report_service.get_dashboard = _async_return({
            "pending_design_count": 2,
            "pending_production_count": 3,
            "pending_installation_count": 1,
            "overdue_order_count": 1,
        })
        composer._get_anomaly_section = _async_return("### 异常提醒\n\n无异常")
        composer._generate_suggestions = _async_return(["建议1"])

        import asyncio
        report = asyncio.run(
            composer.generate_report(period="monthly", year=2026, month=6)
        )

        assert report["period"] == "monthly"
        assert report["year"] == 2026
        assert report["month"] == 6
        assert report["stats"]["order_count"] == 10
        assert report["stats"]["order_amount"] == 100000.0
        assert "2026年6月" in report["narrative"]
        assert "经营报告" in report["narrative"]
        assert len(report["suggestions"]) > 0

    def test_generate_weekly_report_with_mock(self, mock_db):
        """ReportComposer should generate weekly report."""
        from app.ai.rule_based.report_composer import ReportComposer

        composer = ReportComposer(mock_db)
        composer.report_service.get_dashboard = _async_return({
            "today_order_amount": 5000.0,
            "month_order_amount": 50000.0,
            "month_payment_amount": 40000.0,
            "pending_design_count": 1,
            "pending_production_count": 2,
            "pending_installation_count": 0,
            "overdue_order_count": 0,
        })
        composer.report_service.get_daily_report = _async_return({
            "order_count": 3,
            "order_amount": 15000.0,
            "payment_count": 2,
            "payment_amount": 12000.0,
        })
        composer._get_anomaly_section = _async_return("")
        composer._generate_suggestions = _async_return([])

        import asyncio
        report = asyncio.run(
            composer.generate_report(period="weekly", week=26)
        )

        assert report["period"] == "weekly"
        assert report["week"] == 26
        assert "第26周" in report["narrative"]

    def test_suggestions_for_overdue_orders(self, mock_db):
        """Suggestions should include overdue order advice."""
        from app.ai.rule_based.report_composer import ReportComposer

        composer = ReportComposer(mock_db)
        import asyncio
        suggestions = asyncio.run(
            composer._generate_suggestions({"overdue_count": 5})
        )
        assert any("逾期" in s for s in suggestions)

    def test_suggestions_for_low_collection(self, mock_db):
        """Suggestions should include collection advice when rate is low."""
        from app.ai.rule_based.report_composer import ReportComposer

        composer = ReportComposer(mock_db)
        import asyncio
        suggestions = asyncio.run(
            composer._generate_suggestions({"collection_rate": 0.3})
        )
        assert any("收款率" in s for s in suggestions)


class TestBusinessNarrativeSchema:
    def test_business_narrative_response(self):
        from app.ai.schemas.ai_report import BusinessNarrativeResponse
        resp = BusinessNarrativeResponse(
            mode="rule_based",
            period="monthly",
            year=2026,
            month=6,
            narrative="Test narrative",
            suggestions=["S1", "S2"],
        )
        assert resp.mode == "rule_based"
        assert resp.narrative == "Test narrative"
        assert len(resp.suggestions) == 2


def _async_return(value):
    async def fn(*args, **kwargs):
        return value
    return fn
