"""AI Payment OCR API — extract payment info from receipt screenshots."""

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
from app.models.business_document import BusinessDocument
from app.models.customer import Customer
from app.models.user import User
from app.schemas.common import success

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai/payment-ocr",
    tags=["AI Payment OCR"],
    dependencies=[Depends(require_permission(PERM_AI_QUOTE_READ))],
)


def _utc_month_dir() -> str:
    """Return the UTC month used for shared upload archive paths."""
    return datetime.now(UTC).strftime("%Y%m")


@router.post("/recognize")
async def recognize_payment_screenshot(
    file: UploadFile = File(...),
    order_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Upload a payment receipt screenshot and extract payment information.

    - Rule-based: saves the image, returns empty fields + order context for manual entry
    - AI-enhanced: additionally runs OCR, returns extracted amount/payer/date/method
    """
    # 1. Save file
    file_bytes = await file.read()
    month_dir = _utc_month_dir()
    upload_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, month_dir)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "receipt.jpg")[1] or ".jpg"
    save_name = f"{uuid4().hex}{ext}"
    save_path = os.path.join(upload_dir, save_name)

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    image_url = f"/uploads/{month_dir}/{save_name}"

    # 2. Get order context if order_id provided
    order_context = None
    if order_id:
        o_result = await db.execute(
            select(BusinessDocument).where(
                BusinessDocument.doc_type == "order",
                BusinessDocument.id == UUID(order_id),
                BusinessDocument.deleted_at.is_(None),
            )
        )
        order = o_result.scalar_one_or_none()
        if order:
            c_result = await db.execute(
                select(Customer).where(Customer.id == order.customer_id)
            )
            customer = c_result.scalar_one_or_none()
            order_context = {
                "customer_name": customer.name if customer else "未知",
                "unpaid_amount": float(order.unpaid_amount or 0),
                "order_no": order.doc_no,
            }

    # 3. Rule-based: empty fields
    extracted = {
        "amount": None,
        "paid_at": None,
        "payer_name": None,
        "remark": None,
        "payment_method": None,
    }
    mode = "rule_based"
    confidence = "none"

    # 4. AI-enhanced (if configured)
    # Only run AI OCR if a vision-capable model is configured
    _vision_available = False
    try:
        from sqlalchemy import func as _fnc
        from sqlalchemy import select as _sel

        from app.models.ai_model import AIModel
        _qr = await db.execute(_sel(_fnc.count()).select_from(AIModel).where(
            AIModel.supports_vision == True, AIModel.enabled == True
        ))
        _vision_available = _qr.scalar() > 0
    except Exception:  # noqa: BLE001 - optional vision capability probe must keep rule-based OCR available
        pass

    if _vision_available:
        try:
            from app.ai.ai_enhanced.ocr_reader import OCRReader

            client = GatewayAIClient(db)
            reader = OCRReader(client)
            ocr_result = await reader.extract_payment_info(file_bytes, order_context)

            if ocr_result:
                extracted.update({
                    "amount": ocr_result.get("amount"),
                    "paid_at": ocr_result.get("paid_at"),
                    "payer_name": ocr_result.get("payer_name"),
                    "remark": ocr_result.get("remark"),
                    "payment_method": ocr_result.get("payment_method"),
                })
                mode = "ai_enhanced"
                # Confidence based on how many fields were extracted
                filled = sum(1 for v in extracted.values() if v is not None)
                if filled >= 4:
                    confidence = "high"
                elif filled >= 2:
                    confidence = "medium"
                else:
                    confidence = "low"
        except Exception:
            logger.exception("AI OCR enhancement failed, falling back to rule-based")

    return success({
        "mode": mode,
        "image_url": image_url,
        "extracted": extracted,
        "confidence": confidence,
        "order_context": order_context,
    })
