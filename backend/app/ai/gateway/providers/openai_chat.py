"""OpenAI Chat Completions adapter - supports DeepSeek, OpenAI, and all OpenAI-compatible APIs."""
import json
import time
from typing import Any, Optional

import httpx

from app.ai.gateway.providers.base import (
    AIModelResponse, BaseProviderAdapter, ModelConfig, ProviderConfig,
    ProviderTestResult, TestConfig, UnifiedMessage, UnifiedToolCall, UnifiedUsage,
)


class OpenAICompatibleAdapter(BaseProviderAdapter):
    """Adapter for OpenAI Chat Completions API and compatible providers (DeepSeek, etc.)."""

    async def _build_url(self, config: ProviderConfig) -> str:
        if config.full_url_mode and config.endpoint_url:
            return config.endpoint_url
        base = config.base_url.rstrip("/")
        return base + "/chat/completions"

    async def _build_headers(self, config: ProviderConfig) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            prefix = config.auth_prefix or "Bearer"
            headers[config.auth_header] = f"{prefix} {config.api_key}"
        if config.custom_headers:
            headers.update(config.custom_headers)
        return headers

    def _build_messages(self, messages: list[UnifiedMessage]) -> list[dict]:
        import base64
        result = []
        for m in messages:
            if m.images:
                content_blocks = []
                for img_bytes in m.images:
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    media_type = "image/jpeg"
                    try:
                        if img_bytes[:4] == b"\x89PNG":
                            media_type = "image/png"
                        elif img_bytes[:2] == b"\xff\xd8":
                            media_type = "image/jpeg"
                        elif img_bytes[:4] == b"RIFF":
                            media_type = "image/webp"
                        elif img_bytes[:4] == b"GIF8":
                            media_type = "image/gif"
                    except Exception:
                        pass
                    content_blocks.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    })
                content_blocks.append({"type": "text", "text": m.content})
                result.append({"role": m.role, "content": content_blocks})
            else:
                result.append({"role": m.role, "content": m.content})
        return result

    async def chat_completion(
        self,
        messages: list[UnifiedMessage],
        config: ProviderConfig,
        model: ModelConfig,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> AIModelResponse:
        url = await self._build_url(config)
        headers = await self._build_headers(config)

        body: dict[str, Any] = {
            "model": model.upstream_model_code,
            "messages": self._build_messages(messages),
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_output_tokens is not None:
            body["max_tokens"] = max_output_tokens

        start = time.monotonic()
        async with httpx.AsyncClient(verify=config.tls_verify, timeout=config.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=body)
            elapsed_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code != 200:
            err_text = resp.text[:500] if resp.text else "unknown error"
            return AIModelResponse(
                request_id="",
                provider_code="",
                model_code=model.upstream_model_code,
                status="failed",
                latency_ms=elapsed_ms,
                error_code=f"HTTP_{resp.status_code}",
                error_message=err_text,
            )

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        output_text = message.get("content", "")
        usage_data = data.get("usage", {})

        tool_calls_raw = message.get("tool_calls", [])
        tool_calls = []
        for tc in tool_calls_raw:
            try:
                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(UnifiedToolCall(
                id=tc.get("id", ""),
                name=tc.get("function", {}).get("name", ""),
                arguments=args,
            ))

        return AIModelResponse(
            request_id=data.get("id", ""),
            provider_code="",
            model_code=model.upstream_model_code,
            status="success",
            output_text=output_text,
            tool_calls=tool_calls,
            usage=UnifiedUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                cached_input_tokens=usage_data.get("prompt_tokens_details", {}).get("cached_tokens", 0)
                if isinstance(usage_data.get("prompt_tokens_details"), dict) else 0,
                output_tokens=usage_data.get("completion_tokens", 0),
            ),
            latency_ms=elapsed_ms,
            finish_reason=choice.get("finish_reason"),
        )

    async def test_connection(
        self,
        config: ProviderConfig,
        model: ModelConfig,
        test_config: TestConfig,
    ) -> ProviderTestResult:
        """Test connection with a simple text prompt."""
        messages = [UnifiedMessage(role="user", content=test_config.prompt or "Say 'Hello, I am working correctly.'")]
        start = time.monotonic()
        result = await self.chat_completion(
            messages=messages,
            config=config,
            model=model,
            temperature=test_config.temperature or 0.1,
            max_output_tokens=test_config.max_tokens or 50,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if result.status == "failed":
            return ProviderTestResult(
                success=False,
                status_code=int(result.error_code.replace("HTTP_", "")) if result.error_code and result.error_code.startswith("HTTP_") else None,
                latency_ms=elapsed_ms,
                error_code=result.error_code,
                error_message=result.error_message,
            )

        return ProviderTestResult(
            success=True,
            status_code=200,
            latency_ms=elapsed_ms,
            first_token_latency_ms=elapsed_ms,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            output_text=result.output_text,
        )
