"""Tests for AnomalyDetector — rule-based business anomaly detection."""

from __future__ import annotations

from uuid import UUID

# Sample test data
SAMPLE_ORDER_ID = UUID("33333333-3333-3333-3333-333333333333")
SAMPLE_CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")


class TestAnomalyDetector:
    def test_scan_all_returns_empty_when_no_anomalies(self, mock_db):
        """scan_all should return empty lists when no data matches rules."""
        from app.ai.rule_based.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector(mock_db)
        # Override all scan methods to return empty
        detector._scan_underpriced_quotes = _async_return([])
        detector._scan_overdue_orders = _async_return([])
        detector._scan_unpaid_installations = _async_return([])
        detector._scan_credit_exceeded = _async_return([])
        detector._scan_outsource_delays = _async_return([])
        detector._scan_inventory_shortages = _async_return([])

        import asyncio
        result = asyncio.run(detector.scan_all())
        assert result["alerts"] == []
        assert result["summary"]["critical"] == 0
        assert result["summary"]["warning"] == 0
        assert result["summary"]["info"] == 0

    def test_scan_all_aggregates_across_all_rules(self, mock_db):
        """scan_all should aggregate alerts from all scan methods."""
        from app.ai.rule_based.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector(mock_db)
        detector._scan_underpriced_quotes = _async_return([
            {"type": "quote_underpriced", "severity": "warning", "object_type": "quote", "object_id": "1", "title": "T1", "detail": "D1", "created_at": ""},
        ])
        detector._scan_overdue_orders = _async_return([
            {"type": "order_overdue", "severity": "critical", "object_type": "order", "object_id": "2", "title": "T2", "detail": "D2", "created_at": ""},
        ])
        detector._scan_unpaid_installations = _async_return([])
        detector._scan_credit_exceeded = _async_return([])
        detector._scan_outsource_delays = _async_return([])
        detector._scan_inventory_shortages = _async_return([
            {"type": "inventory_low", "severity": "critical", "object_type": "inventory_item", "object_id": "3", "title": "T3", "detail": "D3", "created_at": ""},
            {"type": "inventory_low", "severity": "info", "object_type": "inventory_item", "object_id": "4", "title": "T4", "detail": "D4", "created_at": ""},
        ])

        import asyncio
        result = asyncio.run(detector.scan_all())
        assert len(result["alerts"]) == 4
        assert result["summary"]["critical"] == 2
        assert result["summary"]["warning"] == 1
        assert result["summary"]["info"] == 1

    def test_severity_classification(self):
        """Verify severity values are consistent across the module."""
        from app.ai.rule_based.anomaly_detector import (
            INSTALLATION_TERMINAL_STATES,
            ORDER_TERMINAL_STATES,
            OUTSOURCE_TERMINAL_STATES,
        )
        assert "completed" in ORDER_TERMINAL_STATES
        assert "cancelled" in ORDER_TERMINAL_STATES
        assert "completed" in OUTSOURCE_TERMINAL_STATES
        assert "settled" in OUTSOURCE_TERMINAL_STATES
        assert "completed" in INSTALLATION_TERMINAL_STATES


def test_anomaly_alert_schema_validates():
    """AnomalyAlert schema should accept valid data."""
    from app.ai.schemas.ai_anomaly import AnomalyAlert, AnomalyScanResponse
    alert = AnomalyAlert(
        type="order_overdue",
        severity="warning",
        object_type="order",
        object_id="some-uuid",
        title="Test title",
        detail="Test detail",
    )
    assert alert.type == "order_overdue"
    assert alert.severity == "warning"

    response = AnomalyScanResponse(
        mode="rule_based",
        alerts=[alert],
    )
    assert response.mode == "rule_based"
    assert len(response.alerts) == 1


def test_cdr_calculation_anomaly_check_reports_invalid_inputs():
    """试算异常检查应返回可读异常，而不是把非法输入静默吞掉。"""
    import asyncio

    from app.ai.rule_based.cdr_anomaly_detector import CdrPriceAnomalyDetector

    anomalies = asyncio.run(CdrPriceAnomalyDetector(None).check_calculation({
        "line_no": 2,
        "width_mm": 100,
        "height_mm": 100,
        "hole_area_mm2": 12000,
        "unit_price": -1,
        "quantity": 0,
    }))

    anomaly_types = {item["type"] for item in anomalies}
    assert {
        "hole_area_exceeds_bbox",
        "negative_unit_price",
        "invalid_quantity",
    } <= anomaly_types


def test_cdr_calculation_anomaly_check_ignores_optional_missing_geometry():
    """数量/固定价类报价没有尺寸时不应被误报。"""
    import asyncio

    from app.ai.rule_based.cdr_anomaly_detector import CdrPriceAnomalyDetector

    anomalies = asyncio.run(CdrPriceAnomalyDetector(None).check_calculation({
        "unit_price": 0,
        "quantity": 1,
    }))

    assert anomalies == []


def _async_return(value):
    async def fn(*args, **kwargs):
        return value
    return fn
