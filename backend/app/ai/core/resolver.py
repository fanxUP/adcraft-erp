"""Feature resolver: picks rule-based or AI-enhanced implementation at runtime.

Decides whether AI features are available by checking either:
- AI_ENABLED=true + AI_API_KEY (old AIClient path)
- AI_ENABLED=true + gateway has configured providers (new Gateway path)

Usage:
    if FeatureResolver.is_ai_available():
        # Can use either old AIClient or new GatewayAIClient
        ...
    else:
        # Fall back to rule-based
        ...
"""

from app.core.config import settings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class FeatureResolver:
    """Decides whether AI-enhanced features are available.

    AI features need AI_ENABLED=true AND either:
    - A non-empty AI_API_KEY in settings (for old AIClient), OR
    - An enabled AI provider in the database (for new AIGateway)
    """

    @staticmethod
    def is_ai_available() -> bool:
        return settings.AI_ENABLED and bool(settings.AI_API_KEY)

    @staticmethod
    def is_gateway_available() -> bool:
        return settings.AI_ENABLED

    @staticmethod
    def ai_mode() -> str:
        return "ai_enhanced" if settings.AI_ENABLED else "rule_based"

    @staticmethod
    def create_client(db: "AsyncSession"):
        """Create the appropriate AI client (GatewayAIClient preferred).

        Falls back to old AIClient if Gateway is not available.
        """
        if settings.AI_ENABLED:
            from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient
            return GatewayAIClient(db)
        from app.ai.core.ai_client import AIClient
        return AIClient()
