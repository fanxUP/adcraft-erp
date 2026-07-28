"""GatewayAIClient — adapter wrapping AIGateway with AIClient's interface.

Allows existing AI feature modules (ImageAnalyzer, OCRReader, etc.)
to use the AIGateway without changing their code.
"""
import json
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.gateway import AIGateway

logger = logging.getLogger(__name__)

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


class GatewayAIClient:
    """Adapter that wraps AIGateway with the same public interface as AIClient.

    This lets existing AI feature modules (ImageAnalyzer, OCRReader,
    LLMReportWriter, LLMQuoteAssistant) use the AIGateway without
    changing their code.

    Usage:
        client = GatewayAIClient(db)
        text = await client.chat_completion("分析数据", "你是一个专家")
        result = await client.analyze_image(image_bytes, "分析这张照片")
    """

    def __init__(self, db: AsyncSession, tenant_id: Optional[UUID] = None) -> None:
        self._db = db
        self._tenant_id = tenant_id or TENANT_ID
        self._gateway = AIGateway(db, tenant_id=self._tenant_id)

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
        task_code: str = "prompt_test",
        temperature: float = 0.1,
    ) -> str:
        """Send a chat completion request and return the text response."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = await self._gateway.execute(
            task_code=task_code,
            messages=messages,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return result.output_text or ""

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        task_code: str = "site_photo_analysis",
    ) -> str:
        """Analyze an image using a vision-capable model via the Gateway."""
        import base64 as b64mod

        b64 = b64mod.b64encode(image_bytes).decode("utf-8")
        vision_messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        result = await self._gateway.execute(
            task_code=task_code,
            messages=vision_messages,
            temperature=0.1,
        )
        return result.output_text or ""

    async def ocr_image(
        self,
        image_bytes: bytes,
        order_context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Extract structured payment info from a receipt screenshot."""
        prompt = (
            "Extract the following fields from this payment receipt image. "
            "Return ONLY valid JSON with these keys: "
            "amount (number), paid_at (ISO date string or null), "
            "payer_name (string or null), remark (string or null), "
            "payment_method (string: wechat/alipay/bank_transfer/cash/other or null)."
        )
        if order_context:
            prompt += (
                f"\nOrder context: customer={order_context.get('customer_name', '?')}, "
                f"unpaid={order_context.get('unpaid_amount', '?')}"
            )

        text = await self.analyze_image(image_bytes, prompt, task_code="payment_ocr")
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return {}
