"""AI Business Reports API — smart narrative reports with optional AI enhancement."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.common import success
from app.models.user import User
from app.ai.rule_based.report_composer import ReportComposer
from app.ai.core.resolver import FeatureResolver

router = APIRouter(prefix="/ai/reports", tags=["AI Reports"])


@router.get("/business-narrative")
async def get_business_narrative(
    period: str = Query("monthly", pattern="^(weekly|monthly)$"),
    year: int | None = Query(None),
    month: int | None = Query(None),
    week: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a business narrative report.

    Args:
        period: "weekly" or "monthly"
        year: Report year (defaults to current)
        month: Month for monthly reports
        week: ISO week for weekly reports

    Returns narrative report with stats, narrative text, and suggestions.
    Always works in rule-based mode (template-driven). AI-enhanced mode
    adds free-form LLM narrative when AI is configured.
    """
    composer = ReportComposer(db)
    report = await composer.generate_report(
        period=period,
        year=year,
        month=month,
        week=week,
    )

    mode = "rule_based"

    if FeatureResolver.is_ai_available():
        try:
            from app.ai.core.ai_client import AIClient
            from app.ai.ai_enhanced.llm_report_writer import LLMReportWriter
            writer = LLMReportWriter(AIClient())
            narrative, suggestions = await writer.write_narrative(
                report["stats"], period
            )
            if narrative:
                report["narrative"] = narrative
            if suggestions:
                report["suggestions"] = suggestions
            mode = "ai_enhanced"
        except Exception:
            pass  # Fall back to rule-based on any error

    report["mode"] = mode
    return success(report)
