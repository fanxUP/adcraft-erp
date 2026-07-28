"""AI Gateway v2 — unified entry point with routing, fallback, circuit breaker, and cost tracking.

Business code calls this instead of directly calling any model provider SDK.
The Gateway handles:
  1. Task route resolution (primary model + fallback chain)
  2. Provider selection and API key decryption
  3. Circuit breaker protection per provider
  4. Fallback chain on failure
  5. Request logging and daily usage aggregation
  6. Cost estimation
"""
import json
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.providers.base import (
    AIModelResponse,
    BaseProviderAdapter,
    ModelConfig,
    ProviderConfig,
    UnifiedMessage,
)
from app.ai.gateway.providers.openai_chat import OpenAICompatibleAdapter
from app.ai.gateway.routing.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerError,
    circuit_breaker_registry,
)
from app.ai.gateway.security.secret_store import decrypt_api_key
from app.repositories.ai_model_repo import AIModelRepository
from app.repositories.ai_provider_repo import AIProviderRepository
from app.repositories.ai_request_repo import AIRequestRepository
from app.repositories.ai_task_route_repo import AITaskRouteRepository

logger = logging.getLogger(__name__)

# Protocol adapter registry
_ADAPTERS: dict[str, BaseProviderAdapter] = {
    "openai_chat_completions": OpenAICompatibleAdapter(),
    "openai_responses": OpenAICompatibleAdapter(),
}

# Default pricing per 1K tokens (USD) — used when model pricing not configured
_DEFAULT_INPUT_PRICE_PER_1K = 0.001
_DEFAULT_OUTPUT_PRICE_PER_1K = 0.002


class AIGatewayError(Exception):
    """Raised when the AI Gateway encounters an error that should surface to the caller."""


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing_json: Optional[dict] = None,
) -> tuple[float, str]:
    """Estimate cost in USD based on token usage and model pricing."""
    if pricing_json:
        input_price = float(pricing_json.get("input_price_per_1k", _DEFAULT_INPUT_PRICE_PER_1K))
        output_price = float(pricing_json.get("output_price_per_1k", _DEFAULT_OUTPUT_PRICE_PER_1K))
    else:
        input_price = _DEFAULT_INPUT_PRICE_PER_1K
        output_price = _DEFAULT_OUTPUT_PRICE_PER_1K
    cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
    return round(cost, 8), "USD"


class AIGateway:
    """Unified AI Gateway with routing, fallback, circuit breaker, and cost tracking.

    Usage:
        gateway = AIGateway(db)
        result = await gateway.execute(
            task_code="quote_requirement_extraction",
            messages=[{"role": "user", "content": "..."}],
            user_id="...",
        )
    """

    def __init__(self, db: AsyncSession, tenant_id: Optional[UUID] = None):
        self.db = db
        self._tenant_id = tenant_id
        self._provider_repo = AIProviderRepository(db)
        self._model_repo = AIModelRepository(db)
        self._route_repo = AITaskRouteRepository(db)
        self._request_repo = AIRequestRepository(db)

    # ── Main execute method ──

    async def execute(
        self,
        *,
        task_code: str,
        messages: list[dict],
        model_role: str = "standard",
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        provider_code: Optional[str] = None,
        user_id: Optional[str] = None,
        business_object_type: Optional[str] = None,
        business_object_id: Optional[str] = None,
        input_summary: Optional[str] = None,
    ) -> AIModelResponse:
        """Execute an AI request with routing, fallback, and logging.

        Args:
            task_code: Identifier for the type of task
            messages: List of {"role": str, "content": str} messages
            model_role: fast / standard / reasoning / vision / embedding
            temperature: Optional temperature override
            max_output_tokens: Optional max tokens override
            provider_code: Optional specific provider to use
            user_id: Optional user UUID string
            business_object_type: Optional business entity type
            business_object_id: Optional business entity UUID
            input_summary: Optional short description of input for logs

        Returns:
            AIModelResponse with the result
        """
        request_id = str(uuid.uuid4())
        tenant_id = self._tenant_id or UUID("00000000-0000-0000-0000-000000000000")
        user_uuid = UUID(user_id) if user_id else None
        biz_uuid = UUID(business_object_id) if business_object_id else None

        # Create request log entry
        log_entry = await self._request_repo.create({
            "request_id": request_id,
            "tenant_id": tenant_id,
            "user_id": user_uuid,
            "task_code": task_code,
            "business_object_type": business_object_type,
            "business_object_id": biz_uuid,
            "input_summary": input_summary,
            "status": "pending",
        })

        # Resolve task route config
        route, route_config = await self._resolve_route(task_code, tenant_id)

        # Build the execution chain (primary + fallbacks)
        execution_plan = await self._build_execution_plan(
            task_code=task_code,
            tenant_id=tenant_id,
            model_role=route_config.get("model_role", model_role),
            provider_code=provider_code,
            route=route,
        )

        if not execution_plan:
            # No configured route and no available providers
            raise AIGatewayError("没有可用的 AI 供应商或模型配置")

        # Circuit breaker config
        cb_config = circuit_breaker_registry.get_config(
            route.get("circuit_breaker_json") if route else None
        )

        # Attempt execution with fallback chain
        last_error: Optional[Exception] = None
        attempts = 0
        fallbacks = 0
        response: Optional[AIModelResponse] = None

        for idx, step in enumerate(execution_plan):
            attempts += 1
            if idx > 0:
                fallbacks += 1
                logger.info("Fallback %d/%d: trying provider=%s model=%s",
                            idx, len(execution_plan) - 1,
                            step.get("provider_name", step["provider_id"]),
                            step.get("model_code", "?"))

            try:
                # Get circuit breaker for this provider
                breaker = await circuit_breaker_registry.get_or_create(
                    str(step["provider_id"]), cb_config
                )

                response = await breaker.call(
                    self._execute_single,
                    step, messages, temperature, max_output_tokens,
                )

                # Success — stop the chain
                break

            except CircuitBreakerError as e:
                last_error = e
                logger.warning("Circuit breaker blocked provider=%s: %s", step["provider_id"], e)
                continue
            except AIGatewayError:
                raise
            except Exception as e:
                last_error = e
                logger.warning("Provider call failed provider=%s model=%s: %s",
                               step["provider_id"], step.get("model_code", "?"), e)
                continue

        # Update request log
        update_data: dict[str, Any] = {
            "attempt_count": attempts,
            "fallback_count": fallbacks,
            "status": "completed" if response else "failed",
            "completed_at": datetime.now(timezone.utc),
        }

        if response:
            update_data.update({
                "provider_id": UUID(step["provider_id"]) if step else None,
                "model_id": UUID(step["model_id"]) if (step and step.get("model_id")) else None,
                "model_code": step.get("model_code") if step else None,
                "latency_ms": response.latency_ms,
                "input_tokens": response.usage.input_tokens if response.usage else None,
                "output_tokens": response.usage.output_tokens if response.usage else None,
                "output_summary": response.output_text[:500] if response.output_text else None,
            })

            # Estimate cost
            pricing_json = step.get("pricing_json") if step else None
            cost, currency = _estimate_cost(
                response.usage.input_tokens if response.usage else 0,
                response.usage.output_tokens if response.usage else 0,
                pricing_json,
            )
            update_data["estimated_cost"] = Decimal(str(cost))
            update_data["currency"] = currency
        else:
            update_data.update({
                "error_code": getattr(last_error, "__class__", type(last_error)).__name__ if last_error else "UNKNOWN",
                "error_message_sanitized": str(last_error)[:500] if last_error else "All providers failed",
            })

        await self._request_repo.update(log_entry.id, update_data)

        # Upsert daily usage
        if response:
            today = date.today()
            await self._request_repo.upsert_usage_daily(
                tenant_id=tenant_id,
                usage_date=today,
                provider_id=UUID(step["provider_id"]) if step else None,
                model_id=UUID(step["model_id"]) if (step and step.get("model_id")) else None,
                task_code=task_code,
                input_tokens_delta=response.usage.input_tokens if response.usage else 0,
                output_tokens_delta=response.usage.output_tokens if response.usage else 0,
                cost_delta=float(update_data.get("estimated_cost", 0)),
                latency_ms=response.latency_ms,
                success=True,
            )

        if not response:
            raise AIGatewayError(
                f"AI 请求失败（已尝试 {attempts} 次，含 {fallbacks} 次故障转移）: "
                f"{getattr(last_error, 'message', str(last_error)) if last_error else '所有供应商不可用'}"
            )

        return response

    # ── Internal execution ──

    async def _execute_single(
        self,
        step: dict,
        messages: list[dict],
        temperature: Optional[float],
        max_output_tokens: Optional[int],
    ) -> AIModelResponse:
        """Execute against a single provider/model combination."""
        provider_config = ProviderConfig(
            base_url=step.get("base_url", ""),
            full_url_mode=step.get("full_url_mode", False),
            endpoint_url=step.get("endpoint_url"),
            auth_header=step.get("auth_header", "Authorization"),
            auth_prefix=step.get("auth_prefix", "Bearer"),
            api_key=step.get("api_key", ""),
            custom_headers=step.get("custom_headers", {}),
            timeout_seconds=step.get("timeout_seconds", 60),
            retry_count=step.get("retry_count", 0),
            tls_verify=step.get("tls_verify", True),
        )

        model_config = ModelConfig(
            upstream_model_code=step.get("model_code", ""),
            max_output_tokens=step.get("max_output_tokens"),
            supports_streaming=step.get("supports_streaming", True),
            supports_tools=step.get("supports_tools", False),
            supports_json_schema=step.get("supports_json_schema", False),
            supports_vision=step.get("supports_vision", False),
        )

        adapter = _ADAPTERS.get(step.get("protocol", ""))
        if not adapter:
            raise AIGatewayError(f"不支持的协议: {step.get('protocol')}")

        unified_messages = [
            UnifiedMessage(role=m.get("role", "user"), content=m.get("content", ""))
            for m in messages
        ]

        return await adapter.chat_completion(
            messages=unified_messages,
            config=provider_config,
            model=model_config,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    # ── Route resolution ──

    async def _resolve_route(
        self, task_code: str, tenant_id: UUID
    ) -> tuple[Optional[dict], dict]:
        """Resolve task route configuration for a given task_code."""
        route = None
        if tenant_id:
            route_record = await self._route_repo.get_by_code(tenant_id, task_code)
            if route_record and route_record.enabled:
                route = {
                    "id": str(route_record.id),
                    "task_code": route_record.task_code,
                    "primary_provider_id": str(route_record.primary_provider_id) if route_record.primary_provider_id else None,
                    "primary_model_role": route_record.primary_model_role,
                    "fallback_chain_json": route_record.fallback_chain_json or [],
                    "required_capabilities_json": route_record.required_capabilities_json or {},
                    "timeout_seconds": route_record.timeout_seconds,
                    "circuit_breaker_json": route_record.circuit_breaker_json or {},
                }

        route_config = {}
        if route:
            route_config = {
                "model_role": route.get("primary_model_role", "standard"),
                "timeout_seconds": route.get("timeout_seconds", 60),
            }

        return route, route_config

    async def _build_execution_plan(
        self,
        *,
        task_code: str,
        tenant_id: UUID,
        model_role: str = "standard",
        provider_code: Optional[str] = None,
        route: Optional[dict] = None,
    ) -> list[dict]:
        """Build an ordered list of (provider, model) steps to try.

        Priority:
          1. Route's primary_provider_id + primary_model_role
          2. Route's fallback_chain entries
          3. If provider_code specified → that provider's models
          4. Any enabled provider with matching model role
          5. Any enabled provider with any model
        """
        plan: list[dict] = []
        seen_providers: set[str] = set()

        # Phase 1: Route-based plan
        if route and route.get("primary_provider_id"):
            step = await self._make_step(
                provider_id=route["primary_provider_id"],
                model_role=route.get("primary_model_role", model_role) if route else model_role,
            )
            if step:
                plan.append(step)
                seen_providers.add(str(step["provider_id"]))

        if route and route.get("fallback_chain_json"):
            for fallback in route["fallback_chain_json"]:
                fb_id = fallback.get("provider_id")
                if fb_id and fb_id not in seen_providers:
                    step = await self._make_step(
                        provider_id=fb_id,
                        model_role=fallback.get("model_role", model_role),
                    )
                    if step:
                        plan.append(step)
                        seen_providers.add(fb_id)

        # Phase 2: provider_code override
        if not plan or provider_code:
            if provider_code:
                provider = await self._provider_repo.get_by_code(provider_code)
                if provider and str(provider.id) not in seen_providers:
                    step = await self._make_step(
                        provider_id=str(provider.id),
                        model_role=model_role,
                    )
                    if step:
                        plan.append(step)
                        seen_providers.add(str(provider.id))

        # Phase 3: Any enabled provider with matching role
        if not plan:
            providers, _ = await self._provider_repo.list_all(
                limit=10, enabled_only=True
            )
            for provider in providers:
                pid = str(provider.id)
                if pid in seen_providers:
                    continue
                step = await self._make_step(
                    provider_id=pid,
                    model_role=model_role,
                )
                if step:
                    plan.append(step)
                    seen_providers.add(pid)

            # Phase 4: Any enabled provider, any model
            if not plan:
                for provider in providers:
                    pid = str(provider.id)
                    if pid in seen_providers:
                        continue
                    step = await self._make_step(
                        provider_id=pid,
                        model_role=None,
                    )
                    if step:
                        plan.append(step)
                        seen_providers.add(pid)

        return plan

    async def _make_step(
        self,
        provider_id: str,
        model_role: Optional[str] = None,
    ) -> Optional[dict]:
        """Build an execution step for a provider, finding the best model."""
        provider = await self._provider_repo.get_by_id(UUID(provider_id))
        if not provider or not provider.enabled:
            return None

        # Find matching model
        models, _ = await self._model_repo.list_by_provider(provider.id)
        model = self._pick_best_model(models, model_role)

        if not model:
            return None

        # Get API key
        api_key = ""
        if provider.credential_reference:
            try:
                api_key = decrypt_api_key(provider.credential_reference)
            except Exception:
                logger.error("Failed to decrypt API key for provider %s", provider.provider_name)
                return None

        return {
            "provider_id": str(provider.id),
            "provider_name": provider.provider_name,
            "model_id": str(model.id),
            "model_code": model.upstream_model_code,
            "protocol": provider.protocol,
            "base_url": provider.base_url or "",
            "full_url_mode": provider.full_url_mode,
            "endpoint_url": provider.endpoint_url,
            "auth_header": provider.auth_header,
            "auth_prefix": provider.auth_prefix,
            "api_key": api_key,
            "custom_headers": provider.custom_headers_json or {},
            "timeout_seconds": provider.timeout_seconds,
            "retry_count": provider.retry_count,
            "tls_verify": provider.tls_verify,
            "supports_streaming": model.supports_streaming,
            "supports_tools": model.supports_tools,
            "supports_json_schema": model.supports_json_schema,
            "supports_vision": model.supports_vision,
            "pricing_json": model.pricing_json,
            "max_output_tokens": model.max_output_tokens,
        }

    def _pick_best_model(self, models: list, model_role: Optional[str] = None):
        """Pick the best model from a list, preferring role match then priority."""
        if not models:
            return None

        # Prefer matching role + enabled
        if model_role:
            for m in models:
                if m.model_role == model_role and m.enabled:
                    return m
        # Fallback to any enabled model
        for m in models:
            if m.enabled:
                return m
        # Last resort
        return models[0]
