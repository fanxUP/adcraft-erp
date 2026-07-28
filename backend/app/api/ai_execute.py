"""Unified AI task execution endpoint.

Business modules call this endpoint instead of directly invoking AI providers.
The Gateway handles routing, fallback, circuit breaker, and logging.
"""
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.gateway import AIGateway, AIGatewayError
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.common import success

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI Execution"])


class ExecuteRequest(BaseModel):
    task_code: str = Field(..., min_length=2, max_length=150, description="Task identifier for route resolution")
    messages: list[dict] = Field(..., min_length=1, description="Chat messages [{'role': 'user', 'content': '...'}]")
    model_role: str = Field("standard", description="fast / standard / reasoning / vision / embedding")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=1, le=131072)
    provider_code: Optional[str] = Field(None, description="Optional specific provider to use")
    business_object_type: Optional[str] = None
    business_object_id: Optional[str] = None
    input_summary: Optional[str] = Field(None, max_length=500, description="Brief input description for logging")


@router.post("/ai/tasks/execute")
async def execute_task(
    req: ExecuteRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Unified AI task execution endpoint.

    Routes the request through the AI Gateway, which handles provider selection,
    failover, circuit breaker, and request logging.
    """
    try:
        gateway = AIGateway(db, tenant_id="00000000-0000-0000-0000-000000000001")

        result = await gateway.execute(
            task_code=req.task_code,
            messages=req.messages,
            model_role=req.model_role,
            temperature=req.temperature,
            max_output_tokens=req.max_output_tokens,
            provider_code=req.provider_code,
            user_id=str(current_user.id) if current_user.id else None,
            business_object_type=req.business_object_type,
            business_object_id=req.business_object_id,
            input_summary=req.input_summary,
        )

        return success({
            "text": result.output_text,
            "input_tokens": result.usage.input_tokens if result.usage else None,
            "output_tokens": result.usage.output_tokens if result.usage else None,
            "latency_ms": result.latency_ms,
            "model_code": result.model_code,
        })
    except AIGatewayError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("AI execute failed")
        raise HTTPException(status_code=500, detail=f"AI 执行异常: {str(e)}")
