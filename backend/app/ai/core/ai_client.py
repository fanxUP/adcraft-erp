"""AI client: wraps httpx for LLM API calls.

Only instantiated when AI_ENABLED and AI_API_KEY are configured.
Supports Anthropic Messages API and OpenAI Chat Completions API.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.core.config import settings


class AIClientError(Exception):
    """Raised when AI client is used but not configured."""


class AIAPIError(Exception):
    """Raised on AI API call failure."""


class AIClient:
    """Async HTTP client for AI provider APIs.

    Supports:
    - Anthropic Messages API
    - OpenAI Chat Completions API

    Usage:
        client = AIClient()
        result = await client.chat_completion(
            prompt="分析客户需求...",
            system_prompt="你是一个广告报价专家...",
        )
    """

    def __init__(self) -> None:
        if not settings.AI_API_KEY:
            raise AIClientError("AI_API_KEY is not configured")

        self._provider = settings.AI_PROVIDER
        self._api_key = settings.AI_API_KEY
        self._model = settings.AI_MODEL
        self._max_tokens = settings.AI_MAX_TOKENS
        self._temperature = settings.AI_TEMPERATURE
        self._base_url = settings.AI_API_BASE_URL or self._default_base_url()

    def _default_base_url(self) -> str:
        if self._provider == "anthropic":
            return "https://api.anthropic.com"
        if self._provider == "openai":
            return "https://api.openai.com"
        raise AIClientError(f"Unknown AI provider: {self._provider}")

    # ── Public API ───────────────────────────────────────────────────────

    async def chat_completion(
        self, prompt: str, system_prompt: str = "", max_tokens: int | None = None
    ) -> str:
        """Send a chat completion request and return the text response."""
        if self._provider == "anthropic":
            return await self._anthropic_chat(prompt, system_prompt, max_tokens)
        if self._provider == "openai":
            return await self._openai_chat(prompt, system_prompt, max_tokens)
        raise AIClientError(f"Unsupported provider for chat: {self._provider}")

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        """Analyze an image (site photo, receipt) using a vision-capable model."""
        if self._provider == "anthropic":
            return await self._anthropic_vision(image_bytes, prompt)
        if self._provider == "openai":
            return await self._openai_vision(image_bytes, prompt)
        raise AIClientError(f"Unsupported provider for vision: {self._provider}")

    async def ocr_image(self, image_bytes: bytes) -> dict[str, Any]:
        """Extract structured payment info from a receipt screenshot."""
        prompt = (
            "Extract the following fields from this payment receipt image. "
            "Return ONLY valid JSON with these keys: "
            "amount (number), paid_at (ISO date string or null), "
            "payer_name (string or null), remark (string or null), "
            "payment_method (string: wechat/alipay/bank_transfer/cash/other or null)."
        )
        text = await self.analyze_image(image_bytes, prompt)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    # ── Anthropic Messages API ───────────────────────────────────────────

    async def _anthropic_chat(
        self, prompt: str, system_prompt: str, max_tokens: int | None
    ) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens or self._max_tokens,
            "temperature": self._temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/messages", headers=headers, json=body
            )
            if resp.status_code != 200:
                raise AIAPIError(
                    f"Anthropic API error {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            return data["content"][0]["text"]

    async def _anthropic_vision(self, image_bytes: bytes, prompt: str) -> str:
        media_type = self._guess_image_type(image_bytes)
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/messages", headers=headers, json=body
            )
            if resp.status_code != 200:
                raise AIAPIError(
                    f"Anthropic API error {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            return data["content"][0]["text"]

    # ── OpenAI API ───────────────────────────────────────────────────────

    async def _openai_chat(
        self, prompt: str, system_prompt: str, max_tokens: int | None
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model,
            "max_tokens": max_tokens or self._max_tokens,
            "temperature": self._temperature,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions", headers=headers, json=body
            )
            if resp.status_code != 200:
                raise AIAPIError(
                    f"OpenAI API error {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _openai_vision(self, image_bytes: bytes, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                            },
                        },
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions", headers=headers, json=body
            )
            if resp.status_code != 200:
                raise AIAPIError(
                    f"OpenAI API error {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _guess_image_type(data: bytes) -> str:
        if data[:4] == b"\x89PNG":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF":
            return "image/webp"
        if data[:4] == b"GIF8":
            return "image/gif"
        return "image/jpeg"  # fallback
