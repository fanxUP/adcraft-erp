"""Integration tests for AI API endpoints using FastAPI TestClient.

Tests the full request/response cycle: routing, validation, dependency injection,
response structure, and error handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.deps import get_db, get_current_user
from app.schemas.common import success

SAMPLE_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")


# ── Mock helpers ────────────────────────────────────────────────────

class MockResult:
    def __init__(self, scalar_return=None, scalars_return=None):
        self._scalar = scalar_return
        self._scalars = scalars_return

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._scalars if self._scalars is not None else []


def make_mock_user():
    """Create a mock admin user for auth dependency."""
    from app.models.user import User
    user = MagicMock(spec=User)
    user.id = SAMPLE_USER_ID
    user.username = "testadmin"
    user.real_name = "Test Admin"
    user.is_active = True
    user.roles = ["admin"]
    return user


def make_mock_db():
    """Create a mock async DB session."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MockResult())
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    return make_mock_db()


@pytest.fixture
def mock_user():
    return make_mock_user()


@pytest.fixture
def client(mock_db_session, mock_user):
    """TestClient with overridden dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Authorization headers with a real JWT token."""
    from app.utils.security import create_access_token
    token = create_access_token(SAMPLE_USER_ID, "testadmin")
    return {"Authorization": f"Bearer {token}"}


# ── AI Anomalies ────────────────────────────────────────────────────

class TestAIAnomaliesAPI:
    """GET /api/v1/ai/anomalies/scan"""

    def test_scan_anomalies_returns_success(self, client, auth_headers):
        """Should return 200 with alerts list and summary."""
        response = client.get("/api/v1/ai/anomalies/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "alerts" in data["data"]
        assert "summary" in data["data"]
        assert "mode" in data["data"]

    def test_scan_anomalies_requires_auth(self, mock_db_session):
        """Should return 401 when no auth header and no dependency override."""
        # Only override DB, NOT auth — so the real auth check runs
        app.dependency_overrides[get_db] = lambda: mock_db_session
        try:
            with TestClient(app) as c:
                response = c.get("/api/v1/ai/anomalies/scan")
                assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_scan_anomalies_with_mocked_data(self, client, auth_headers, mock_db_session):
        """Should aggregate alerts from all scan methods."""
        from app.ai.rule_based.anomaly_detector import AnomalyDetector

        with patch.object(AnomalyDetector, "scan_all", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = {
                "alerts": [
                    {
                        "type": "order_overdue", "severity": "critical",
                        "object_type": "order", "object_id": "o1",
                        "title": "Overdue", "detail": "5 days overdue",
                        "created_at": "2026-06-30T00:00:00",
                    },
                ],
                "summary": {"critical": 1, "warning": 0, "info": 0},
            }
            response = client.get("/api/v1/ai/anomalies/scan", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()["data"]
            assert len(data["alerts"]) == 1
            assert data["summary"]["critical"] == 1


# ── AI Knowledge Base ──────────────────────────────────────────────

class TestAIKnowledgeAPI:
    """GET /api/v1/ai/knowledge/similar-quotes and /search-by-description"""

    def test_similar_quotes_requires_keyword(self, client, auth_headers):
        """Should return 422 when keyword is missing."""
        response = client.get("/api/v1/ai/knowledge/similar-quotes", headers=auth_headers)
        assert response.status_code == 422

    def test_similar_quotes_with_keyword(self, client, auth_headers):
        """Should return results when keyword is provided."""
        with patch("app.ai.api.ai_knowledge.QuoteFinder") as mock_finder_cls:
            mock_finder = MagicMock()
            mock_finder.find_similar = AsyncMock(return_value=(
                [],
                {"price_range": [1000, 5000], "avg_price": 3000,
                 "avg_margin": 0.25, "recommended_price": 3000},
            ))
            mock_finder_cls.return_value = mock_finder

            response = client.get(
                "/api/v1/ai/knowledge/similar-quotes",
                params={"keyword": "文化墙"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert "items" in data
            assert "pricing_summary" in data
            assert data["mode"] == "rule_based"

    def test_similar_quotes_with_all_params(self, client, auth_headers):
        """Should accept optional area/material params."""
        with patch("app.ai.api.ai_knowledge.QuoteFinder") as mock_finder_cls:
            mock_finder = MagicMock()
            mock_finder.find_similar = AsyncMock(return_value=([], {
                "price_range": [], "avg_price": 0, "avg_margin": 0,
                "recommended_price": 0,
            }))
            mock_finder_cls.return_value = mock_finder

            response = client.get(
                "/api/v1/ai/knowledge/similar-quotes",
                params={
                    "keyword": "PVC",
                    "min_area": 5,
                    "max_area": 20,
                    "material_ids": "11111111-1111-1111-1111-111111111111",
                    "limit": 10,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

    def test_search_by_description_requires_min_length(self, client, auth_headers):
        """Should return 422 when description is too short."""
        response = client.get(
            "/api/v1/ai/knowledge/search-by-description",
            params={"description": "ab"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_search_by_description_returns_keywords(self, client, auth_headers):
        """Should extract keywords and return results."""
        with patch("app.ai.api.ai_knowledge.QuoteFinder") as mock_finder_cls:
            mock_finder = MagicMock()
            mock_finder.extract_keywords = AsyncMock(return_value=["文化墙", "PVC"])
            mock_finder.find_similar = AsyncMock(return_value=([], {
                "price_range": [], "avg_price": 0, "avg_margin": 0,
                "recommended_price": 0,
            }))
            mock_finder_cls.return_value = mock_finder

            response = client.get(
                "/api/v1/ai/knowledge/search-by-description",
                params={"description": "6m×2m PVC文化墙制作安装"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert "extracted_keywords" in data
            assert "pvc" in [k.lower() for k in data["extracted_keywords"]] or "文化墙" in data["extracted_keywords"]


# ── AI Quote Assistant ─────────────────────────────────────────────

class TestAIQuoteAPI:
    """POST /api/v1/ai/quotes/assist and /assist/save"""

    def test_assist_quote_requires_description(self, client, auth_headers):
        """Should return 422 when description is missing."""
        response = client.post("/api/v1/ai/quotes/assist", json={}, headers=auth_headers)
        assert response.status_code == 422

    def test_assist_quote_requires_min_description_length(self, client, auth_headers):
        """Should return 422 when description is too short."""
        response = client.post(
            "/api/v1/ai/quotes/assist",
            json={"description": "ab"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_assist_quote_returns_draft(self, client, auth_headers):
        """Should return a structured quote draft."""
        with patch("app.ai.api.ai_quote.FeatureResolver") as mock_resolver:
            mock_resolver.ai_mode.return_value = "rule_based"
            mock_resolver.is_ai_available.return_value = False

            response = client.post(
                "/api/v1/ai/quotes/assist",
                json={"description": "6m×2m PVC文化墙制作安装"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert "project_name" in data
            assert "items" in data
            assert "total_estimate" in data
            assert "confidence" in data

    def test_assist_quote_with_customer_id(self, client, auth_headers):
        """Should accept optional customer_id."""
        with patch("app.ai.api.ai_quote.FeatureResolver") as mock_resolver:
            mock_resolver.ai_mode.return_value = "rule_based"
            mock_resolver.is_ai_available.return_value = False

            response = client.post(
                "/api/v1/ai/quotes/assist",
                json={
                    "description": "大型户外广告牌制作安装",
                    "customer_id": str(SAMPLE_CUSTOMER_ID),
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

    def test_save_assisted_quote_invalid_data(self, client, auth_headers):
        """Should handle empty draft gracefully."""
        from app.services.quote_service import QuoteService

        with patch.object(QuoteService, "create_quote", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"id": str(uuid4()), "project_name": "Test"}
            with patch.object(QuoteService, "calculate_quote", new_callable=AsyncMock) as mock_calc:
                mock_calc.return_value = {"id": str(uuid4()), "project_name": "Test", "total_amount": 0}

                response = client.post(
                    "/api/v1/ai/quotes/assist/save",
                    json={"project_name": "Test", "items": []},
                    headers=auth_headers,
                )
                # Should not crash even with no items
                assert response.status_code == 200


# ── AI Reports ─────────────────────────────────────────────────────

class TestAIReportsAPI:
    """GET /api/v1/ai/reports/business-narrative"""

    def test_business_narrative_defaults(self, client, auth_headers):
        """Should return monthly report with default params."""
        with patch("app.ai.api.ai_reports.ReportComposer") as mock_composer_cls:
            mock_composer = MagicMock()
            mock_composer.generate_report = AsyncMock(return_value={
                "period": "monthly", "year": 2026, "month": 6,
                "stats": {"order_count": 0, "order_amount": 0},
                "narrative": "Test report", "suggestions": [],
            })
            mock_composer_cls.return_value = mock_composer

            response = client.get(
                "/api/v1/ai/reports/business-narrative",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["period"] == "monthly"
            assert "narrative" in data

    def test_business_narrative_weekly(self, client, auth_headers):
        """Should accept weekly period."""
        with patch("app.ai.api.ai_reports.ReportComposer") as mock_composer_cls:
            mock_composer = MagicMock()
            mock_composer.generate_report = AsyncMock(return_value={
                "period": "weekly", "year": 2026, "week": 26,
                "stats": {}, "narrative": "", "suggestions": [],
            })
            mock_composer_cls.return_value = mock_composer

            response = client.get(
                "/api/v1/ai/reports/business-narrative",
                params={"period": "weekly", "week": 26},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["period"] == "weekly"

    def test_business_narrative_invalid_period(self, client, auth_headers):
        """Should return 422 for invalid period value."""
        response = client.get(
            "/api/v1/ai/reports/business-narrative",
            params={"period": "daily"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_business_narrative_with_specific_month(self, client, auth_headers):
        """Should accept year and month params."""
        with patch("app.ai.api.ai_reports.ReportComposer") as mock_composer_cls:
            mock_composer = MagicMock()
            mock_composer.generate_report = AsyncMock(return_value={
                "period": "monthly", "year": 2026, "month": 3,
                "stats": {}, "narrative": "", "suggestions": [],
            })
            mock_composer_cls.return_value = mock_composer

            response = client.get(
                "/api/v1/ai/reports/business-narrative",
                params={"year": 2026, "month": 3},
                headers=auth_headers,
            )
            assert response.status_code == 200


# ── AI Site Photo ──────────────────────────────────────────────────

class TestAISitePhotoAPI:
    """POST /api/v1/ai/site-photos/analyze"""

    def test_analyze_requires_file(self, client, auth_headers):
        """Should return 422 when no file is uploaded."""
        response = client.post("/api/v1/ai/site-photos/analyze", headers=auth_headers)
        assert response.status_code == 422

    def test_analyze_with_image(self, client, auth_headers, tmp_path):
        """Should save image and return checklist."""
        # Create a tiny fake image
        image_content = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
            b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Mock settings to use temp dir
        with patch("app.ai.api.ai_site_photo.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(tmp_path)
            mock_settings.AI_ENABLED = False

            response = client.post(
                "/api/v1/ai/site-photos/analyze",
                files={"file": ("test.jpg", image_content, "image/jpeg")},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["mode"] == "rule_based"
            assert "photo_url" in data
            assert "checklist" in data
            assert data["checklist"]["wall_condition"] == "awaiting_review"
            assert data["ai_findings"] is None

    def test_analyze_with_task_id(self, client, auth_headers, tmp_path):
        """Should accept optional installation_task_id."""
        image_content = b"fake_image_bytes"

        with patch("app.ai.api.ai_site_photo.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(tmp_path)
            mock_settings.AI_ENABLED = False

            response = client.post(
                "/api/v1/ai/site-photos/analyze",
                files={"file": ("photo.png", image_content, "image/png")},
                params={"installation_task_id": str(uuid4()), "remark": "墙况检查"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["checklist"]["notes"] == "墙况检查"


# ── AI Payment OCR ─────────────────────────────────────────────────

class TestAIPaymentOCRAPI:
    """POST /api/v1/ai/payment-ocr/recognize"""

    def test_recognize_requires_file(self, client, auth_headers):
        """Should return 422 when no file is uploaded."""
        response = client.post("/api/v1/ai/payment-ocr/recognize", headers=auth_headers)
        assert response.status_code == 422

    def test_recognize_with_image(self, client, auth_headers, tmp_path):
        """Should save image and return empty extraction (rule-based)."""
        image_content = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
            b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("app.ai.api.ai_payment_ocr.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(tmp_path)
            mock_settings.AI_ENABLED = False

            response = client.post(
                "/api/v1/ai/payment-ocr/recognize",
                files={"file": ("receipt.jpg", image_content, "image/jpeg")},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["mode"] == "rule_based"
            assert data["confidence"] == "none"
            assert data["extracted"]["amount"] is None
            assert data["extracted"]["paid_at"] is None
            assert "image_url" in data

    def test_recognize_with_order_id(self, client, auth_headers, tmp_path):
        """Should accept optional order_id and include order_context when found."""
        image_content = b"fake_receipt"

        with patch("app.ai.api.ai_payment_ocr.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(tmp_path)
            mock_settings.AI_ENABLED = False

            response = client.post(
                "/api/v1/ai/payment-ocr/recognize",
                files={"file": ("receipt.png", image_content, "image/png")},
                params={"order_id": str(uuid4())},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]
            # order_context is None when order not found (mocked DB returns nothing)
            assert data["order_context"] is None


# ── Response Structure Consistency ──────────────────────────────────

class TestAIResponseConsistency:
    """All AI endpoints should return the standard ApiResponse envelope."""

    ENDPOINTS = [
        ("GET", "/api/v1/ai/anomalies/scan", {}),
        ("GET", "/api/v1/ai/knowledge/similar-quotes", {"keyword": "test"}),
        ("GET", "/api/v1/ai/knowledge/search-by-description", {"description": "test description long enough"}),
        ("GET", "/api/v1/ai/reports/business-narrative", {}),
    ]

    def test_all_get_endpoints_return_standard_envelope(self, client, auth_headers):
        """All GET AI endpoints should return {code, message, data}."""
        for method, path, params in self.ENDPOINTS:
            with patch("app.ai.api.ai_reports.ReportComposer.generate_report",
                       new_callable=AsyncMock) as mock_report:
                mock_report.return_value = {
                    "period": "monthly", "year": 2026, "month": 6,
                    "stats": {}, "narrative": "", "suggestions": [],
                }
                response = client.request(method, path, params=params, headers=auth_headers)
                assert response.status_code in (200, 422), f"{method} {path} returned {response.status_code}"
                if response.status_code == 200:
                    body = response.json()
                    assert "code" in body, f"{path} missing 'code'"
                    assert "data" in body, f"{path} missing 'data'"
