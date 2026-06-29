"""Tests for AI FeatureResolver — decides rule-based vs AI-enhanced path."""

from __future__ import annotations

import pytest


class TestFeatureResolver:
    def test_is_ai_available_returns_false_by_default(self):
        """Without AI_ENABLED and API key, AI should be unavailable."""
        from app.ai.core.resolver import FeatureResolver
        assert FeatureResolver.is_ai_available() is False

    def test_ai_mode_returns_rule_based_when_disabled(self):
        """When AI is disabled, mode should be 'rule_based'."""
        from app.ai.core.resolver import FeatureResolver
        assert FeatureResolver.ai_mode() == "rule_based"

    def test_feature_resolver_is_static(self):
        """FeatureResolver methods should work without instantiation."""
        from app.ai.core.resolver import FeatureResolver
        resolver = FeatureResolver()
        assert resolver.is_ai_available() is False
        assert resolver.ai_mode() == "rule_based"


class TestAIClient:
    def test_ai_client_raises_without_api_key(self, monkeypatch):
        """AIClient should raise AIClientError when API key is empty."""
        import app.ai.core.ai_client as client_module
        monkeypatch.setattr(client_module.settings, "AI_API_KEY", "")
        from app.ai.core.ai_client import AIClient, AIClientError
        with pytest.raises(AIClientError, match="API_KEY"):
            AIClient()

    def test_ai_client_creates_with_api_key(self, monkeypatch):
        """AIClient should instantiate when API key is set."""
        import app.ai.core.ai_client as client_module
        monkeypatch.setattr(client_module.settings, "AI_API_KEY", "fake-key")
        monkeypatch.setattr(client_module.settings, "AI_PROVIDER", "anthropic")
        monkeypatch.setattr(client_module.settings, "AI_MODEL", "claude-test")
        from app.ai.core.ai_client import AIClient
        client = AIClient()
        assert client._provider == "anthropic"
        assert client._api_key == "fake-key"

    def test_ai_client_raises_for_unknown_provider(self, monkeypatch):
        """AIClient should raise for unknown provider."""
        import app.ai.core.ai_client as client_module
        monkeypatch.setattr(client_module.settings, "AI_API_KEY", "fake-key")
        monkeypatch.setattr(client_module.settings, "AI_PROVIDER", "unknown")
        from app.ai.core.ai_client import AIClient, AIClientError
        with pytest.raises(AIClientError, match="provider"):
            AIClient()
