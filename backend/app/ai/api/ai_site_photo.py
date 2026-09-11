"""AI Site Photo API — analyze installation site photos for risks."""

import logging
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import PERM_AI_QUOTE_READ, require_permission
from app.models.user import User
from app.schemas.common import success

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/site-photos",
    tags=["AI Site Photos"],
    dependencies=[Depends(require_permission(PERM_AI_QUOTE_READ))],
)


def _utc_month_dir() -> str:
    """Return the UTC month used for shared upload archive paths."""
    return datetime.now(UTC).strftime("%Y%m")


@router.post("/analyze")
async def analyze_site_photo(
    file: UploadFile = File(...),
    installation_task_id: str = Query(None),
    remark: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Upload and analyze an installation site photo.

    - Rule-based: saves the photo, returns empty checklist for manual entry
    - AI-enhanced: additionally runs vision model analysis, returns findings

    Returns checklist + AI findings (when available).
    """
    # 1. Save file
    file_bytes = await file.read()
    month_dir = _utc_month_dir()
    upload_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, month_dir)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    save_name = f"{uuid4().hex}{ext}"
    save_path = os.path.join(upload_dir, save_name)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    photo_url = f"/uploads/{month_dir}/{save_name}"

    # 2. Rule-based: empty checklist
    checklist = {
        "wall_condition": "awaiting_review",
        "height_risk": "awaiting_review",
        "scaffolding_needed": "awaiting_review",
        "obstacles_found": "awaiting_review",
        "cost_impact_estimated": False,
        "notes": remark or "",
    }

    mode = "rule_based"
    ai_findings = None

    # 3. AI-enhanced (if configured)
    # Only run AI analysis if a vision-capable model is configured
    _vision_available = False
    try:
        from sqlalchemy import func as _fnc
        from sqlalchemy import select as _sel

        from app.models.ai_model import AIModel
        _qr = await db.execute(_sel(_fnc.count()).select_from(AIModel).where(
            AIModel.supports_vision == True, AIModel.enabled == True
        ))
        _vision_available = _qr.scalar() > 0
    except Exception:  # noqa: BLE001 - optional vision capability probe must keep rule-based analysis available
        pass

    if _vision_available:
        try:
            from app.ai.ai_enhanced.image_analyzer import ImageAnalyzer

            task_context = None
            if installation_task_id:
                from app.models.task import InstallationTask
                result = await db.execute(
                    select(InstallationTask).where(
                        InstallationTask.id == UUID(installation_task_id)
                    )
                )
                task = result.scalar_one_or_none()
                if task:
                    task_context = {
                        "project_name": task.project_name,
                        "address": getattr(task, "installation_address", None),
                    }

            client = GatewayAIClient(db)
            analyzer = ImageAnalyzer(client)
            ai_findings = await analyzer.analyze_site_photo(file_bytes, task_context)
            mode = "ai_enhanced"

            if ai_findings:
                checklist.update({
                    "wall_condition": ai_findings.get("wall_condition", "awaiting_review"),
                    "height_risk": ai_findings.get("height_risk", "awaiting_review"),
                    "scaffolding_needed": ai_findings.get("scaffolding_needed", "awaiting_review"),
                    "obstacles_found": ai_findings.get("obstacles_found", "awaiting_review"),
                    "cost_impact_estimated": ai_findings.get("cost_impact", "") != "无影响",
                    "notes": ai_findings.get("notes", "") or checklist["notes"],
                })
        except Exception:
            logger.exception("AI image analysis failed, falling back to rule-based")

    return success({
        "mode": mode,
        "photo_url": photo_url,
        "checklist": checklist,
        "ai_findings": ai_findings,
    })
