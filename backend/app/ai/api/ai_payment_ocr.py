"""AI Payment OCR API — extract payment info from receipt screenshots."""

import os
from uuid import uuid4, UUID
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.schemas.common import success
from app.models.user import User
from app.models.order import Order
from app.models.customer import Customer
from app.ai.core.resolver import FeatureResolver

router = APIRouter(prefix="/ai/payment-ocr", tags=["AI Payment OCR"])


@router.post("/recognize")
async def recognize_payment_screenshot(
    file: UploadFile = File(...),
    order_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a payment receipt screenshot and extract payment information.

    - Rule-based: saves the image, returns empty fields + order context for manual entry
    - AI-enhanced: additionally runs OCR, returns extracted amount/payer/date/method
    """
    # 1. Save file
    file_bytes = await file.read()
    month_dir = datetime.now().strftime("%Y%m")
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
            select(Order).where(Order.id == UUID(order_id), Order.deleted_at.is_(None))
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
                "order_no": order.order_no,
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
    if FeatureResolver.is_ai_available():
        try:
            from app.ai.core.ai_client import AIClient
            from app.ai.ai_enhanced.ocr_reader import OCRReader

            client = AIClient()
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
            pass  # Graceful fallback

    return success({
        "mode": mode,
        "image_url": image_url,
        "extracted": extracted,
        "confidence": confidence,
        "order_context": order_context,
    })
