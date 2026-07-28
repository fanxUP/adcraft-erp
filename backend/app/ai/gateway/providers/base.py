"""Base Provider Adapter - all protocol adapters inherit from this."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UnifiedMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    images: list[bytes] = field(default_factory=list)  # raw image bytes for vision


@dataclass
class UnifiedToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class UnifiedUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ProviderConfig:
    base_url: str
    full_url_mode: bool
    endpoint_url: Optional[str]
    auth_header: str
    auth_prefix: Optional[str]
    api_key: str
    custom_headers: dict
    timeout_seconds: int
    retry_count: int
    tls_verify: bool


@dataclass
class ModelConfig:
    upstream_model_code: str
    max_output_tokens: Optional[int]
    supports_streaming: bool
    supports_tools: bool
    supports_json_schema: bool
    supports_vision: bool


@dataclass
class TestConfig:
    test_type: str  # "connection" | "text" | "stream" | "schema" | "tools" | "vision"
    prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    output_schema: Optional[dict] = None


@dataclass
class ProviderTestResult:
    success: bool
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    first_token_latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    output_text: Optional[str] = None
    output_json: Optional[dict] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    capabilities_verified: dict = field(default_factory=dict)


@dataclass
class AIModelResponse:
    request_id: str
    provider_code: str
    model_code: str
    status: str  # "success" | "partial" | "failed"
    output_text: Optional[str] = None
    output_json: Optional[dict] = None
    tool_calls: list[UnifiedToolCall] = field(default_factory=list)
    usage: UnifiedUsage = field(default_factory=UnifiedUsage)
    latency_ms: int = 0
    finish_reason: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class BaseProviderAdapter(ABC):
    """Abstract base for all provider protocol adapters."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[UnifiedMessage],
        config: ProviderConfig,
        model: ModelConfig,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> AIModelResponse:
        """Send a chat completion request and return the response."""
        ...

    @abstractmethod
    async def test_connection(
        self,
        config: ProviderConfig,
        model: ModelConfig,
        test_config: TestConfig,
    ) -> ProviderTestResult:
        """Run a connectivity / capability test against the provider."""
        ...
