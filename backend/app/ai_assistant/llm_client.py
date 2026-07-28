"""LLM client wrapper — uses existing GatewayAIClient."""

from app.ai.core.resolver import FeatureResolver


class LlmClient:
    """Wraps GatewayAIClient for AI Assistant use."""

    def __init__(self, db):
        self.db = db
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = FeatureResolver.create_client(self.db)
        return self._client

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request and return the response text."""
        client = self._get_client()
        return await client.chat_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            task_code="ai_assistant_intent",
            temperature=temperature,
        )

    def is_available(self) -> bool:
        """Check if AI is configured and available."""
        return FeatureResolver.is_gateway_available()
