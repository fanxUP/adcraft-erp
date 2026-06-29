"""Feature resolver: picks rule-based or AI-enhanced implementation at runtime.

Usage:
    resolver = FeatureResolver()
    if resolver.is_ai_available():
        assistant = LLMQuoteAssistant(db, resolver.ai_client())
    else:
        assistant = QuoteFinder(db)
"""

from app.core.config import settings


class FeatureResolver:
    """Decides whether AI-enhanced features are available.

    AI features need both AI_ENABLED=true AND a non-empty AI_API_KEY.
    If either is missing, rule-based implementations are used instead.
    """

    @staticmethod
    def is_ai_available() -> bool:
        return settings.AI_ENABLED and bool(settings.AI_API_KEY)

    @staticmethod
    def ai_mode() -> str:
        return "ai_enhanced" if FeatureResolver.is_ai_available() else "rule_based"
