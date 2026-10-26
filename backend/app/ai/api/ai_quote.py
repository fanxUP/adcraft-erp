"""AI Quote Assistant API — generate draft quotes from natural language descriptions."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.core.resolver import FeatureResolver
from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient
from app.ai.rule_based.quote_finder import QuoteFinder
from app.ai.schemas.ai_quote import AIQuoteAssistRequest
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import (
    PERM_AI_QUOTE_READ,
    PERM_ORDER_CREATE,
    require_all_permissions,
    require_permission,
)
from app.models.user import User
from app.schemas.common import success

router = APIRouter(
    prefix="/ai/quotes",
    tags=["AI Quotes"],
    dependencies=[Depends(require_permission(PERM_AI_QUOTE_READ))],
)


@router.post("/assist")
async def assist_quote(
    data: AIQuoteAssistRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a structured quote draft from natural language description.

    Uses:
    - Rule-based: keyword extraction + catalog matching + historical quotes
    - AI-enhanced (if configured): LLM parses NL into structured quote items

    Returns a draft quote with items, pricing estimate, and similar historical quotes.
    """
    mode = "ai_enhanced" if FeatureResolver.is_gateway_available() else "rule_based"

    if FeatureResolver.is_gateway_available():
        from app.ai.ai_enhanced.llm_quote_assistant import LLMQuoteAssistant
        assistant = LLMQuoteAssistant(db, GatewayAIClient(db))
    else:
        assistant = QuoteFinder(db)

    result = await assistant.generate_quote_draft(data.description, data.customer_id)
    result["mode"] = mode
    return success(result)


@router.post("/assist/save")
async def save_assisted_quote(
    draft: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(PERM_AI_QUOTE_READ, PERM_ORDER_CREATE)),
):
    """Save an AI-generated draft as a real Quote in 'draft' status.

    The draft data comes from POST /ai/quotes/assist.
    Creates a Quote entity that can be further edited and confirmed.
    """
    from uuid import UUID
    from app.schemas.order import OrderCreate
    from app.services.order_management_service import OrderManagementService
    from app.services.business_document_service import _business_today
    request = OrderCreate(request_id=UUID(str(draft.get("request_id"))), order_date=draft.get("order_date") or _business_today(),
        header={"project_name": draft.get("project_name") or "新项目", "customer_id": draft.get("customer_id"),
                "customer_name": draft.get("customer_name"), "remark": draft.get("ai_analysis", "")},
        items=draft.get("items") or [])
    return success(await OrderManagementService(db, current_user).create(request.model_dump()))


# ── Smart Pricing Recommendation ──


class SmartPriceRequest(BaseModel):
    product_id: str | None = None
    material_id: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    quantity: float = 1


@router.post("/pricing/recommend")
async def recommend_price(
    req: SmartPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get smart pricing recommendation based on historical data."""
    from app.ai.ai_enhanced.llm_quote_assistant import SmartPricingRecommendation
    engine = SmartPricingRecommendation(db)
    result = await engine.recommend_price(
        product_id=req.product_id,
        material_id=req.material_id,
        width_mm=req.width_mm,
        height_mm=req.height_mm,
        quantity=req.quantity,
    )
    return success(result)
