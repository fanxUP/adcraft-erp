"""AI Site Photo API — analyze installation site photos for risks."""

import os
from uuid import uuid4, UUID
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.schemas.common import success
from app.models.user import User
from app.ai.core.resolver import FeatureResolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/site-photos", tags=["AI Site Photos"])


@router.post("/analyze")
async def analyze_site_photo(
    file: UploadFile = File(...),
    installation_task_id: str = Query(None),
    remark: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and analyze an installation site photo.

    - Rule-based: saves the photo, returns empty checklist for manual entry
    - AI-enhanced: additionally runs vision model analysis, returns findings

    Returns checklist + AI findings (when available).
    """
    # 1. Save file
    file_bytes = await file.read()
    month_dir = datetime.now().strftime("%Y%m")
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
    if FeatureResolver.is_ai_available():
        try:
            from app.ai.core.ai_client import AIClient
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

            client = AIClient()
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
