"""AI-enhanced OCR reader — extract payment info from receipt screenshots.

Requires AI_ENABLED=true and AI_API_KEY.
Uses vision model to OCR WeChat/Alipay/bank transfer screenshots.
"""

from __future__ import annotations

import json

from app.ai.core.ai_client import AIClient

SYSTEM_PROMPT = """你是一个财务收款凭证的OCR识别助手。请从提供的收款截图/照片中提取以下信息。

请返回严格 JSON 格式。如果某项信息无法从图片中识别，该字段值设为 null：
{
  "amount": 5000.00,
  "paid_at": "2026-06-29",
  "payer_name": "张三",
  "remark": "付款备注内容",
  "payment_method": "wechat"
}

字段说明：
- amount: 收款金额（数字，如 5000.00）
- paid_at: 收款日期（ISO 格式 YYYY-MM-DD，无法识别则为 null）
- payer_name: 付款方姓名/公司名（无法识别则为 null）
- remark: 付款备注/转账说明（无法识别则为 null）
- payment_method: 支付方式（wechat/alipay/bank_transfer/cash/other，无法识别则为 null）
"""


class OCRReader:
    """AI-powered OCR reader for payment receipt screenshots.

    Usage:
        client = AIClient()
        reader = OCRReader(client)
        extracted = await reader.extract_payment_info(image_bytes, order_context)
    """

    def __init__(self, ai_client: AIClient) -> None:
        self.ai_client = ai_client

    async def extract_payment_info(
        self, image_bytes: bytes, order_context: dict | None = None
    ) -> dict | None:
        """Extract payment information from a receipt image.

        Args:
            image_bytes: Raw image file bytes
            order_context: Optional dict with order info (customer_name, unpaid_amount, etc.)

        Returns:
            Extracted fields dict matching OCRExtracted schema, or None on failure
        """
        prompt = "请从这张收款截图中提取付款信息。"
        if order_context:
            prompt += (
                f"\n关联订单信息：客户「{order_context.get('customer_name', '未知')}」，"
                f"未收金额 ¥{order_context.get('unpaid_amount', '未知')}"
            )

        text = await self.ai_client.analyze_image(image_bytes, prompt)
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
