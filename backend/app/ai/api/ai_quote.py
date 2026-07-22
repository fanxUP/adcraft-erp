"""AI Quote Assistant API — generate draft quotes from natural language descriptions."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.common import success
from app.ai.schemas.ai_quote import AIQuoteAssistRequest
from app.models.user import User
from app.ai.rule_based.quote_finder import QuoteFinder
from app.ai.core.resolver import FeatureResolver

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
    mode = FeatureResolver.ai_mode()

    if FeatureResolver.is_ai_available():
        from app.ai.core.ai_client import AIClient
        from app.ai.ai_enhanced.llm_quote_assistant import LLMQuoteAssistant
        client = AIClient()
        assistant = LLMQuoteAssistant(db, client)
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
    from app.services.quote_service import QuoteService
    service = QuoteService(db)

    quote_data = {
        "project_name": draft.get("project_name", "新项目"),
        "customer_id": draft.get("customer_id"),
        "sales_user_id": str(current_user.id),
        "remark": draft.get("ai_analysis", ""),
    }
    quote = await service.create_quote(quote_data)

    # Add items via service
    from uuid import UUID as _UUID
    items_data = [
        {
            "item_name": item_data.get("item_name", ""),
            "product_id": item_data.get("product_id"),
            "material_id": item_data.get("material_id"),
            "process_id": item_data.get("process_id"),
            "length": item_data.get("length"),
            "width": item_data.get("width"),
            "height": item_data.get("height"),
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
        quote = await service.add_items(str(quote["id"]), items_data)

    return success(quote)
