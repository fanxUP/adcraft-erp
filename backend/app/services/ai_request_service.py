"""Business logic for AI Request logging and usage tracking."""
from datetime import date
from typing import Any, Optional
from uuid import UUID

from app.repositories.ai_request_repo import AIRequestRepository


class AIRequestService:
    def __init__(self, repo: AIRequestRepository):
        self.repo = repo

    async def list_requests(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        task_code: Optional[str] = None,
        status: Optional[str] = None,
        provider_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        records, total = await self.repo.list_all(
            tenant_id, page=page, page_size=page_size,
            task_code=task_code, status=status, provider_id=provider_id,
            start_date=start_date, end_date=end_date,
        )
        return {
            "items": [self._to_dict(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        task_code: Optional[str] = None,
    ) -> dict:
        records = await self.repo.get_usage_summary(
            tenant_id, start_date=start_date, end_date=end_date, task_code=task_code
        )
        # Aggregate
        total_requests = 0
        total_success = 0
        total_failed = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        items_by_date: dict[str, dict] = {}

        for r in records:
            date_key = r.usage_date.isoformat()
            if date_key not in items_by_date:
                items_by_date[date_key] = {
                    "usage_date": date_key,
                    "request_count": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost": 0.0,
                    "avg_latency_ms": None,
                }
            d = items_by_date[date_key]
            d["request_count"] += r.request_count
            d["success_count"] += r.success_count
            d["failed_count"] += r.failed_count
            d["input_tokens"] += r.input_tokens
            d["output_tokens"] += r.output_tokens
            d["estimated_cost"] += float(r.estimated_cost or 0)
            total_requests += r.request_count
            total_success += r.success_count
            total_failed += r.failed_count
            total_input_tokens += r.input_tokens
            total_output_tokens += r.output_tokens
            total_cost += float(r.estimated_cost or 0)

        return {
            "summary": {
                "total_requests": total_requests,
                "total_success": total_success,
                "total_failed": total_failed,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost": round(total_cost, 6),
            },
            "items": list(items_by_date.values()),
        }

    def _to_dict(self, record) -> dict:
        return {
            "id": str(record.id),
            "request_id": record.request_id,
            "tenant_id": str(record.tenant_id),
            "user_id": str(record.user_id) if record.user_id else None,
            "task_code": record.task_code,
            "provider_id": str(record.provider_id) if record.provider_id else None,
            "model_id": str(record.model_id) if record.model_id else None,
            "model_code": record.model_code,
            "business_object_type": record.business_object_type,
            "business_object_id": str(record.business_object_id) if record.business_object_id else None,
            "input_summary": record.input_summary,
            "output_summary": record.output_summary,
            "status": record.status,
            "attempt_count": record.attempt_count,
            "fallback_count": record.fallback_count,
            "latency_ms": record.latency_ms,
            "first_token_latency_ms": record.first_token_latency_ms,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "estimated_cost": float(record.estimated_cost) if record.estimated_cost else None,
            "currency": record.currency,
            "error_code": record.error_code,
            "error_message_sanitized": record.error_message_sanitized,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }
