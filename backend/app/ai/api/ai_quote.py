"""AI Quote Assistant API — generate draft quotes from natural language descriptions."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.common import success
from app.ai.schemas.ai_quote import AIQuoteAssistRequest
from app.models.user import User
from app.ai.rule_based.quote_finder import QuoteFinder
from app.ai.core.resolver import FeatureResolver
from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient

router = APIRouter(prefix="/ai/quotes", tags=["AI Quotes"])


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
    current_user: User = Depends(get_current_user),
):
    """Save an AI-generated draft as a real Quote in 'draft' status.

    The draft data comes from POST /ai/quotes/assist.
    Creates a Quote entity that can be further edited and confirmed.
    """
    from app.services.business_document_service import BusinessDocumentService
    service = BusinessDocumentService(db, doc_type='quote')

    quote_data = {
        "project_name": draft.get("project_name", "新项目"),
        "customer_id": draft.get("customer_id"),
        "sales_user_id": str(current_user.id),
        "remark": draft.get("ai_analysis", ""),
    }
    quote = await service.create(quote_data)

    # Add items via service
    from uuid import UUID as _UUID
    items_data = [
        {
            "item_name": item_data.get("item_name", ""),
            "product_id": item_data.get("product_id"),
            "material_id": item_data.get("material_id"),
            "process_id": item_data.get("process_id"),
            "material_process": item_data.get("material_process"),
            "width": item_data.get("length") or item_data.get("width"),
            "height": item_data.get("width") if item_data.get("length") else item_data.get("height"),
            "quantity": item_data.get("quantity", 1),
            "unit": item_data.get("unit", "㎡"),
            "unit_price": item_data.get("unit_price", 0),
            "design_fee": item_data.get("design_fee", 0),
            "installation_fee": item_data.get("installation_fee", 0),
            "process_fee": item_data.get("process_fee", 0),
            "transport_fee": item_data.get("transport_fee", 0),
            "other_fee": item_data.get("other_fee", 0),
            "remark": item_data.get("remark", ""),
        }
        for item_data in draft.get("items", [])
    ]
    if items_data:
        quote = await service.add_items(_UUID(quote["id"]), items_data)

    return success(quote)


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
