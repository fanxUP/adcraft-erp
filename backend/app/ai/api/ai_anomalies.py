"""AI Anomaly Alerts API — rule-based business anomaly detection."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.core.resolver import FeatureResolver
from app.ai.rule_based.anomaly_detector import AnomalyDetector
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import PERM_AI_ANOMALY_READ, require_permission
from app.models.user import User
from app.schemas.common import success

router = APIRouter(
    prefix="/ai/anomalies",
    tags=["AI Anomalies"],
    dependencies=[Depends(require_permission(PERM_AI_ANOMALY_READ))],
)


@router.get("/scan")
async def scan_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan all business anomalies across 6 rule categories.

    Returns all detected anomalies with severity classification and summary.
    Always available — pure rule-based, no AI dependency.
    """
    detector = AnomalyDetector(db)
    result = await detector.scan_all()
    result["mode"] = FeatureResolver.ai_mode()
    return success(result)
