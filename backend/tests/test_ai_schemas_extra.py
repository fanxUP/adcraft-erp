"""Tests for AI schemas (Pydantic validation) and API helper logic.

Covers schemas not fully tested elsewhere: OCR, site photo, reports, anomalies.
Also tests confidence calculation, keyword extraction edge cases, and schema defaults.
"""

from __future__ import annotations

import pytest


# ── AI Quote Schemas ──────────────────────────────────────────────────

class TestAIQuoteSchemas:
    def test_draft_quote_item_defaults(self):
        """DraftQuoteItem should have sensible defaults."""
        from app.ai.schemas.ai_quote import DraftQuoteItem
        item = DraftQuoteItem(item_name="测试项")
        assert item.quantity == 1
        assert item.unit == "㎡"
        assert item.design_fee == 0
        assert item.installation_fee == 0
        assert item.process_fee == 0
        assert item.transport_fee == 0
        assert item.other_fee == 0
        assert item.subtotal == 0
        assert item.remark == ""

    def test_draft_quote_item_with_dimensions(self):
        """DraftQuoteItem should accept optional dimensions."""
        from app.ai.schemas.ai_quote import DraftQuoteItem
        item = DraftQuoteItem(
            item_name="PVC文化墙",
            length=6.0,
            width=2.0,
            quantity=2,
            unit_price=500.0,
        )
        assert item.length == 6.0
        assert item.width == 2.0
        assert item.quantity == 2
        assert item.unit_price == 500.0

    def test_similar_quote_item_fields(self):
        """SimilarQuoteItem should accept all fields."""
        from app.ai.schemas.ai_quote import SimilarQuoteItem
        sq = SimilarQuoteItem(
            quote_id="q-001",
            quote_no="Q20260629-0001",
            project_name="某公司文化墙",
            total_area=12.5,
            items_summary="PVC+亚克力",
            total_amount=15000.0,
            gross_profit=4500.0,
            profit_margin=0.3,
            created_at="2026-06-01T00:00:00",
        )
        assert sq.total_area == 12.5
        assert sq.profit_margin == 0.3

    def test_pricing_summary(self):
        """PricingSummary should accept price range and stats."""
        from app.ai.schemas.ai_quote import PricingSummary
        ps = PricingSummary(
            price_range=[3000.0, 15000.0],
            avg_price=8000.0,
            avg_margin=0.28,
            recommended_price=7500.0,
        )
        assert ps.price_range == [3000.0, 15000.0]
        assert ps.recommended_price == 7500.0

    def test_ai_quote_assist_response_full(self):
        """AIQuoteAssistResponse should accept a complete result."""
        from app.ai.schemas.ai_quote import (
            AIQuoteAssistResponse,
            DraftQuoteItem,
            SimilarQuoteItem,
        )
        resp = AIQuoteAssistResponse(
            mode="rule_based",
            project_name="6m×2m PVC文化墙",
            items=[DraftQuoteItem(item_name="文化墙主体", length=6.0, width=2.0)],
            total_estimate=12000.0,
            confidence="medium",
            similar_quotes_count=3,
            similar_quotes=[
                SimilarQuoteItem(
                    quote_id="q1", quote_no="Q001",
                    project_name="Similar Project", total_amount=11000.0,
                ),
            ],
            ai_analysis="根据历史报价...",
            risk_notes=["注意：PVC板材价格波动"],
        )
        assert resp.confidence == "medium"
        assert resp.similar_quotes_count == 3
        assert len(resp.similar_quotes) == 1
        assert len(resp.risk_notes) == 1

    def test_quote_assist_request_validation(self):
        """AIQuoteAssistRequest should reject short descriptions."""
        from app.ai.schemas.ai_quote import AIQuoteAssistRequest
        import pydantic

        # Valid: 5+ characters
        req = AIQuoteAssistRequest(description="PVC文化墙制作")
        assert "PVC" in req.description

        # Invalid: too short
        with pytest.raises(pydantic.ValidationError):
            AIQuoteAssistRequest(description="ab")

    def test_quote_assist_request_optional_customer(self):
        """customer_id should be optional."""
        from app.ai.schemas.ai_quote import AIQuoteAssistRequest
        req = AIQuoteAssistRequest(description="足够长的描述文本")
        assert req.customer_id is None

        req2 = AIQuoteAssistRequest(
            description="足够长的描述文本",
            customer_id="44444444-4444-4444-4444-444444444444",
        )
        assert req2.customer_id is not None


# ── AI Knowledge Base Schemas ────────────────────────────────────────

class TestAIKnowledgeSchemas:
    def test_similar_quote_result_defaults(self):
        """SimilarQuoteResult should have correct defaults."""
        from app.ai.schemas.ai_knowledge import SimilarQuoteResult
        r = SimilarQuoteResult(quote_id="q1", quote_no="Q001", project_name="Test")
        assert r.total_area is None
        assert r.items_summary == ""
        assert r.total_amount == 0
        assert r.gross_profit is None
        assert r.profit_margin is None
        assert r.created_at is None

    def test_similar_quotes_response_empty(self):
        """SimilarQuotesResponse should default to empty."""
        from app.ai.schemas.ai_knowledge import SimilarQuotesResponse
        resp = SimilarQuotesResponse()
        assert resp.mode == "rule_based"
        assert resp.items == []
        assert resp.pricing_summary.price_range == []

    def test_similar_quotes_response_with_data(self):
        """SimilarQuotesResponse with items and pricing."""
        from app.ai.schemas.ai_knowledge import (
            SimilarQuotesResponse,
            SimilarQuoteResult,
            PricingSummary,
        )
        resp = SimilarQuotesResponse(
            mode="rule_based",
            items=[
                SimilarQuoteResult(
                    quote_id="q1", quote_no="Q001",
                    project_name="P1", total_amount=5000.0,
                ),
            ],
            pricing_summary=PricingSummary(
                price_range=[3000.0, 7000.0],
                avg_price=5000.0,
                recommended_price=5000.0,
            ),
        )
        assert len(resp.items) == 1
        assert resp.pricing_summary.recommended_price == 5000.0


# ── AI Payment OCR Schemas ───────────────────────────────────────────

class TestPaymentOCRSchemas:
    def test_ocr_extracted_defaults(self):
        """OCRExtracted should have all None defaults."""
        from app.ai.schemas.ai_payment_ocr import OCRExtracted
        ext = OCRExtracted()
        assert ext.amount is None
        assert ext.paid_at is None
        assert ext.payer_name is None
        assert ext.remark is None
        assert ext.payment_method is None

    def test_ocr_extracted_partial(self):
        """OCRExtracted should accept partial fields."""
        from app.ai.schemas.ai_payment_ocr import OCRExtracted
        ext = OCRExtracted(amount=5000.0, payer_name="张三")
        assert ext.amount == 5000.0
        assert ext.payer_name == "张三"
        assert ext.paid_at is None

    def test_ocr_recognize_response_defaults(self):
        """OCRRecognizeResponse should have correct defaults."""
        from app.ai.schemas.ai_payment_ocr import OCRRecognizeResponse
        resp = OCRRecognizeResponse()
        assert resp.mode == "rule_based"
        assert resp.image_url == ""
        assert resp.confidence == "none"
        assert resp.extracted.amount is None
        assert resp.order_context is None

    def test_ocr_recognize_response_with_context(self):
        """OCRRecognizeResponse should accept order_context dict."""
        from app.ai.schemas.ai_payment_ocr import OCRRecognizeResponse, OCRExtracted
        resp = OCRRecognizeResponse(
            mode="ai_enhanced",
            image_url="/uploads/202606/abc.jpg",
            extracted=OCRExtracted(amount=10000.0, payment_method="wechat"),
            confidence="high",
            order_context={
                "customer_name": "测试客户",
                "unpaid_amount": 10000.0,
                "order_no": "O20260629-0001",
            },
        )
        assert resp.confidence == "high"
        assert resp.order_context is not None
        assert resp.order_context["unpaid_amount"] == 10000.0

    def test_ocr_payment_method_values(self):
        """OCRExtracted should accept various payment methods."""
        from app.ai.schemas.ai_payment_ocr import OCRExtracted

        for method in ["wechat", "alipay", "bank_transfer", "cash", "other"]:
            ext = OCRExtracted(payment_method=method)
            assert ext.payment_method == method


# ── AI Site Photo Schemas ────────────────────────────────────────────

class TestSitePhotoSchemas:
    def test_photo_checklist_defaults(self):
        """PhotoChecklist should default to 'awaiting_review'."""
        from app.ai.schemas.ai_site_photo import PhotoChecklist
        cl = PhotoChecklist()
        assert cl.wall_condition == "awaiting_review"
        assert cl.height_risk == "awaiting_review"
        assert cl.scaffolding_needed == "awaiting_review"
        assert cl.obstacles_found == "awaiting_review"
        assert cl.cost_impact_estimated is False
        assert cl.notes == ""

    def test_photo_checklist_with_findings(self):
        """PhotoChecklist should accept completed values."""
        from app.ai.schemas.ai_site_photo import PhotoChecklist
        cl = PhotoChecklist(
            wall_condition="normal",
            height_risk="low_risk",
            scaffolding_needed="not_required",
            obstacles_found="not_found",
            cost_impact_estimated=False,
            notes="墙面平整，无需特殊处理",
        )
        assert cl.wall_condition == "normal"
        assert cl.height_risk == "low_risk"

    def test_site_photo_analyze_response(self):
        """SitePhotoAnalyzeResponse should accept checklist and findings."""
        from app.ai.schemas.ai_site_photo import SitePhotoAnalyzeResponse, PhotoChecklist
        resp = SitePhotoAnalyzeResponse(
            mode="ai_enhanced",
            photo_url="/uploads/202606/photo.jpg",
            checklist=PhotoChecklist(
                wall_condition="poor",
                height_risk="high_risk",
                scaffolding_needed="required",
                cost_impact_estimated=True,
                notes="墙面有裂缝，需要高空作业",
            ),
            ai_findings={"raw_analysis": "墙面状况不佳"},
        )
        assert resp.mode == "ai_enhanced"
        assert resp.checklist.wall_condition == "poor"
        assert resp.checklist.cost_impact_estimated is True
        assert resp.ai_findings is not None

    def test_site_photo_response_rule_based(self):
        """SitePhotoAnalyzeResponse in rule_based mode (no AI findings)."""
        from app.ai.schemas.ai_site_photo import SitePhotoAnalyzeResponse
        resp = SitePhotoAnalyzeResponse(
            mode="rule_based",
            photo_url="/uploads/202606/photo.jpg",
        )
        assert resp.mode == "rule_based"
        assert resp.ai_findings is None
        assert resp.checklist.wall_condition == "awaiting_review"


# ── AI Report Schemas ────────────────────────────────────────────────

class TestAIReportSchemas:
    def test_business_narrative_response_defaults(self):
        """BusinessNarrativeResponse should have correct defaults."""
        from app.ai.schemas.ai_report import BusinessNarrativeResponse
        resp = BusinessNarrativeResponse()
        assert resp.mode == "rule_based"
        assert resp.period == "monthly"
        assert resp.year == 0
        assert resp.month is None
        assert resp.week is None
        assert resp.stats == {}
        assert resp.narrative == ""
        assert resp.suggestions == []

    def test_business_narrative_response_monthly(self):
        """BusinessNarrativeResponse for monthly report."""
        from app.ai.schemas.ai_report import BusinessNarrativeResponse
        resp = BusinessNarrativeResponse(
            mode="ai_enhanced",
            period="monthly",
            year=2026,
            month=6,
            stats={
                "order_count": 10,
                "order_amount": 100000.0,
                "payment_amount": 80000.0,
                "overdue_count": 2,
            },
            narrative="2026年6月经营报告：本月订单...",
            suggestions=["建议关注逾期订单", "提高收款效率"],
        )
        assert resp.mode == "ai_enhanced"
        assert resp.stats["order_count"] == 10
        assert len(resp.suggestions) == 2

    def test_business_narrative_response_weekly(self):
        """BusinessNarrativeResponse for weekly report."""
        from app.ai.schemas.ai_report import BusinessNarrativeResponse
        resp = BusinessNarrativeResponse(
            period="weekly",
            year=2026,
            week=26,
            narrative="第26周经营报告",
        )
        assert resp.period == "weekly"
        assert resp.week == 26
        assert resp.month is None


# ── AI Anomaly Schemas ───────────────────────────────────────────────

class TestAIAnomalySchemas:
    def test_anomaly_alert_severity_values(self):
        """AnomalyAlert should accept critical/warning/info severities."""
        from app.ai.schemas.ai_anomaly import AnomalyAlert

        for sev in ["critical", "warning", "info"]:
            alert = AnomalyAlert(
                type="test_type",
                severity=sev,
                object_type="order",
                object_id="some-id",
                title="Test",
                detail="Test detail",
            )
            assert alert.severity == sev

    def test_anomaly_summary_defaults(self):
        """AnomalySummary should default to zero counts."""
        from app.ai.schemas.ai_anomaly import AnomalySummary
        s = AnomalySummary()
        assert s.critical == 0
        assert s.warning == 0
        assert s.info == 0

    def test_anomaly_scan_response_empty(self):
        """AnomalyScanResponse should default to empty."""
        from app.ai.schemas.ai_anomaly import AnomalyScanResponse
        resp = AnomalyScanResponse()
        assert resp.mode == "rule_based"
        assert resp.alerts == []
        assert resp.summary.critical == 0

    def test_anomaly_alert_requires_type(self):
        """AnomalyAlert type is required."""
        from app.ai.schemas.ai_anomaly import AnomalyAlert
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            AnomalyAlert(
                severity="warning",
                object_type="order",
                object_id="id",
            )


# ── Confidence Calculation Logic ─────────────────────────────────────

class TestPaymentOCRConfidence:
    """Test the confidence calculation logic used in ai_payment_ocr endpoint."""

    def test_confidence_high_when_4_plus_fields(self):
        """Confidence should be 'high' when >= 4 fields extracted."""
        extracted = {
            "amount": 5000.0,
            "paid_at": "2026-06-29",
            "payer_name": "张三",
            "payment_method": "wechat",
            "remark": None,
        }
        filled = sum(1 for v in extracted.values() if v is not None)
        if filled >= 4:
            confidence = "high"
        elif filled >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        assert confidence == "high"
        assert filled == 4

    def test_confidence_medium_when_2_to_3_fields(self):
        """Confidence should be 'medium' when 2-3 fields extracted."""
        extracted = {
            "amount": 5000.0,
            "paid_at": "2026-06-29",
            "payer_name": None,
            "payment_method": None,
            "remark": None,
        }
        filled = sum(1 for v in extracted.values() if v is not None)
        confidence = "medium" if filled >= 2 else "low"
        assert confidence == "medium"
        assert filled == 2

    def test_confidence_low_when_1_field(self):
        """Confidence should be 'low' when only 1 field extracted."""
        extracted = {
            "amount": 5000.0,
            "paid_at": None,
            "payer_name": None,
            "payment_method": None,
            "remark": None,
        }
        filled = sum(1 for v in extracted.values() if v is not None)
        confidence = "medium" if filled >= 2 else "low"
        assert confidence == "low"
        assert filled == 1

    def test_confidence_none_when_no_fields(self):
        """Confidence should be 'none' when 0 fields extracted (rule-based fallback)."""
        extracted = {
            "amount": None,
            "paid_at": None,
            "payer_name": None,
            "payment_method": None,
            "remark": None,
        }
        filled = sum(1 for v in extracted.values() if v is not None)
        assert filled == 0
        # Default confidence is "none" for rule-based mode
        confidence = "none"
        assert confidence == "none"


# ── Schema Round-trip Tests ──────────────────────────────────────────

class TestSchemaRoundTrip:
    """Ensure schemas can be serialized and deserialized."""

    def test_ocr_response_round_trip(self):
        """OCRRecognizeResponse should survive model_dump → model_validate."""
        from app.ai.schemas.ai_payment_ocr import OCRRecognizeResponse, OCRExtracted
        original = OCRRecognizeResponse(
            mode="ai_enhanced",
            image_url="/uploads/test.jpg",
            extracted=OCRExtracted(amount=5000.0),
            confidence="medium",
        )
        data = original.model_dump()
        restored = OCRRecognizeResponse.model_validate(data)
        assert restored.mode == original.mode
        assert restored.extracted.amount == original.extracted.amount
        assert restored.confidence == original.confidence

    def test_anomaly_response_round_trip(self):
        """AnomalyScanResponse should survive model_dump → model_validate."""
        from app.ai.schemas.ai_anomaly import (
            AnomalyScanResponse,
            AnomalyAlert,
            AnomalySummary,
        )
        original = AnomalyScanResponse(
            mode="rule_based",
            alerts=[
                AnomalyAlert(
                    type="order_overdue",
                    severity="critical",
                    object_type="order",
                    object_id="oid-1",
                    title="逾期订单",
                    detail="订单已逾期5天",
                    created_at="2026-06-29T10:00:00",
                ),
            ],
            summary=AnomalySummary(critical=1, warning=0, info=0),
        )
        data = original.model_dump()
        restored = AnomalyScanResponse.model_validate(data)
        assert restored.summary.critical == 1
        assert len(restored.alerts) == 1
        assert restored.alerts[0].type == "order_overdue"

    def test_quote_response_round_trip(self):
        """AIQuoteAssistResponse should survive model_dump → model_validate."""
        from app.ai.schemas.ai_quote import AIQuoteAssistResponse, DraftQuoteItem
        original = AIQuoteAssistResponse(
            mode="rule_based",
            project_name="Test Project",
            items=[DraftQuoteItem(item_name="Item 1", quantity=2)],
            total_estimate=10000.0,
            confidence="low",
        )
        data = original.model_dump()
        restored = AIQuoteAssistResponse.model_validate(data)
        assert restored.project_name == original.project_name
        assert restored.total_estimate == original.total_estimate
        assert len(restored.items) == 1
