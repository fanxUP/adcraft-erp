"""AI-enhanced quote assistant — uses LLM to parse NL requirements into structured quotes.

Requires AI_ENABLED=true and AI_API_KEY.
Falls back to rule-based QuoteFinder when AI is not available.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.core.ai_client import AIClient, AIClientError, AIAPIError
from app.ai.rule_based.quote_finder import QuoteFinder
from app.models.product import Product, Material, Process

SYSTEM_PROMPT = """你是一个广告制作行业的报价专家。用户会用自然语言描述客户需求，你需要分析需求并生成结构化的报价草稿。

请返回 JSON，格式如下：
{
  "project_name": "项目名称",
  "items": [
    {
      "item_name": "项目名称",
      "length": 6.0,
      "width": 2.0,
      "quantity": 1,
      "unit": "㎡",
      "unit_price": 150.0,
      "design_fee": 500.0,
      "installation_fee": 300.0,
      "process_fee": 0,
      "transport_fee": 100.0,
      "other_fee": 0,
      "remark": "备注"
    }
  ],
  "analysis": "分析说明",
  "risk_notes": ["风险1", "风险2"]
}

注意：
- 面积计算公式：length × width × quantity
- 如果用户没有明确尺寸，使用合理的默认值
- design_fee 一般 300-800 元（简单设计）或 800-2000 元（复杂设计）
- installation_fee 一般 100-500 元/㎡ 或按项目估算
- 高空作业需要特别标注风险
"""


class LLMQuoteAssistant:
    """AI-enhanced quote draft generator using LLM.

    Usage:
        client = AIClient()
        assistant = LLMQuoteAssistant(db, client)
        result = await assistant.generate_quote_draft("6m×2m PVC文化墙 含安装")
    """

    def __init__(self, db: AsyncSession, ai_client: AIClient) -> None:
        self.db = db
        self.ai_client = ai_client
        self._rule_based = QuoteFinder(db)

    async def generate_quote_draft(
        self, description: str, customer_id: str | None = None
    ) -> dict:
        """Generate a quote draft from natural language description.

        Falls back to rule-based if AI call fails.
        """
        # Get catalog context
        catalog = await self._build_catalog_context()

        user_prompt = f"产品/材质/工艺目录：\n{catalog}\n\n客户需求：{description}"

        try:
            response = await self.ai_client.chat_completion(
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
            )
            ai_data = self._parse_response(response)

            # Cross-check items against catalog
            validated_items = await self._validate_items(ai_data.get("items", []))

            # Get similar quotes for pricing reference
            finder = QuoteFinder(self.db)
            keywords = await finder.extract_keywords(description)
            similar_quotes, pricing = await finder.find_similar(
                keyword=" ".join(keywords) if keywords else description,
                limit=3,
            )

            return {
                "project_name": ai_data.get("project_name", "新项目"),
                "items": validated_items,
                "total_estimate": pricing.get("recommended_price", 0),
                "confidence": "high",
                "similar_quotes_count": len(similar_quotes),
                "similar_quotes": similar_quotes,
                "ai_analysis": ai_data.get("analysis", ""),
                "risk_notes": ai_data.get("risk_notes", []),
            }

        except (AIClientError, AIAPIError):
            # Fall back to rule-based
            return await self._rule_based.compose_draft_quote(description, customer_id)

    async def _build_catalog_context(self) -> str:
        """Build a concise catalog summary for the LLM prompt."""
        lines: list[str] = []

        prod_result = await self.db.execute(
            select(Product).limit(20)
        )
        products = prod_result.scalars().all()
        if products:
            lines.append("--- 产品 ---")
            for p in products:
                lines.append(f"- {p.name}（默认单价 ¥{float(p.default_price or 0):.2f}）")

        mat_result = await self.db.execute(
            select(Material).limit(20)
        )
        materials = mat_result.scalars().all()
        if materials:
            lines.append("--- 材质 ---")
            for m in materials:
                lines.append(f"- {m.name}（售价 ¥{float(m.sale_price or 0):.2f}）")

        proc_result = await self.db.execute(
            select(Process).limit(10)
        )
        processes = proc_result.scalars().all()
        if processes:
            lines.append("--- 工艺 ---")
            for p in processes:
                lines.append(f"- {p.name}（收费 ¥{float(p.default_price or 0):.2f}）")

        return "\n".join(lines) if lines else "暂无产品/材质/工艺数据"

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    async def _validate_items(self, items: list[dict]) -> list[dict]:
        """Validate AI-generated items have reasonable values."""
        for item in items:
            item.setdefault("quantity", 1)
            item.setdefault("unit", "㎡")
            item.setdefault("design_fee", 0)
            item.setdefault("installation_fee", 0)
            item.setdefault("process_fee", 0)
            item.setdefault("transport_fee", 0)
            item.setdefault("other_fee", 0)
            item.setdefault("subtotal", 0)
            item.setdefault("remark", "")
            # Ensure numeric fields are floats
            for field in ("length", "width", "height"):
                if field in item and item[field] is not None:
                    item[field] = float(item[field])
            for field in ("unit_price", "design_fee", "installation_fee", "process_fee", "transport_fee", "other_fee"):
                if field in item and item[field] is not None:
                    item[field] = float(item[field])
        return items
