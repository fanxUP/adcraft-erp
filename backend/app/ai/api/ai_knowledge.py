"""AI Knowledge Base API — historical quote search and pricing recommendations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.common import success
from app.models.user import User
from app.ai.rule_based.quote_finder import QuoteFinder
from app.ai.core.resolver import FeatureResolver

router = APIRouter(prefix="/ai/knowledge", tags=["AI Knowledge Base"])


@router.get("/similar-quotes")
async def find_similar_quotes(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    min_area: float | None = Query(None, description="最小面积(㎡)"),
    max_area: float | None = Query(None, description="最大面积(㎡)"),
    material_ids: str | None = Query(None, description="材质ID列表，逗号分隔"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search historical quotes by keyword, area range, and material.

    Returns similar quotes with pricing statistics.
    """
    mat_ids: list[UUID] | None = None
    if material_ids:
        mat_ids = [UUID(uid.strip()) for uid in material_ids.split(",") if uid.strip()]

    finder = QuoteFinder(db)
    items, pricing = await finder.find_similar(
        keyword=keyword,
        min_area=min_area,
        max_area=max_area,
        material_ids=mat_ids,
        limit=limit,
    )
    return success({
        "mode": FeatureResolver.ai_mode(),
        "items": items,
        "pricing_summary": pricing,
    })


@router.get("/search-by-description")
async def search_by_description(
    description: str = Query(..., min_length=5, description="自然语言描述的需求"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract keywords from NL description and return matching quotes."""
    finder = QuoteFinder(db)
    keywords = await finder.extract_keywords(description)
    keyword_str = " ".join(keywords) if keywords else description
    items, pricing = await finder.find_similar(keyword=keyword_str, limit=limit)
    return success({
        "mode": FeatureResolver.ai_mode(),
        "items": items,
        "pricing_summary": pricing,
        "extracted_keywords": keywords,
    })
