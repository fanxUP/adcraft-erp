"""AI-enhanced quote assistant v2 — smarter pricing with historical context."""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.core.ai_client import AIClient, AIClientError, AIAPIError
from app.ai.gateway.gateway import AIGatewayError
from app.ai.rule_based.quote_finder import QuoteFinder
from app.models.product import Product, Material, Process
from app.models.business_document import BusinessDocument, BusinessDocumentItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的广告制作报价专家。用户会用自然语言描述客户需求，你需要分析需求并生成结构化的报价草稿。

## 核心原则
1. 必须按照给出的产品/材质/工艺目录选择物料，不要凭空编造
2. 单价优先参考目录中的默认价格，根据项目复杂度适当浮动（±30%）
3. 设计费（design_fee）：简单排版设计 200-500元，复杂创意设计 800-2000元
4. 安装费（installation_fee）：室内简易安装 100-300元/项，高空/复杂安装 500-2000元/项
5. 运输费（transport_fee）：市内 50-200元，城郊 200-500元
6. 如果用户提到特定尺寸，准确计算面积；如果没提到尺寸，给出合理估算并注明"估算"

## 返回格式
```json
{
  "project_name": "项目名称（简洁明了）",
  "items": [
    {
      "item_name": "项目名称",
      "product_id": null,
      "material_process": "产品 / 材质 / 工艺",
      "width": 6.0,
      "height": 2.0,
      "quantity": 1,
      "unit": "㎡",
      "unit_price": 150.0,
      "design_fee": 500.0,
      "installation_fee": 300.0,
      "process_fee": 0,
      "transport_fee": 100.0,
      "other_fee": 0,
      "remark": "",
      "key_spec": "6m×2m"
    }
  ],
  "analysis": "简要分析客户需求，列出本项目的关键考虑因素",
  "risk_notes": [
    "可能的风险项1（如：高空作业需要安全措施）",
    "可能的风险项2"
  ],
  "pricing_notes": "价格制定的依据说明"
}
```

## 注意事项
- 面积 = width × height × quantity（当 unit 为 ㎡ 时）
- 产品ID如果匹配到目录中的组合，请填入对应ID；material_process 填写完整的产品/材质/工艺组合
- key_spec 填写该项目的关键规格描述
- 总价不需要计算在JSON中，前端会自动计算
"""


class LLMQuoteAssistant:
    """AI-enhanced quote draft generator using LLM with historical pricing context."""

    def __init__(self, db: AsyncSession, ai_client: AIClient) -> None:
        self.db = db
        self.ai_client = ai_client
        self._rule_based = QuoteFinder(db)

    async def generate_quote_draft(
        self, description: str, customer_id: str | None = None
    ) -> dict:
        """Generate a quote draft with AI-enhanced pricing recommendations.

        Falls back to rule-based QuoteFinder if AI call fails.
        """
        try:
            # 1. Build context blocks
            catalog = await self._build_catalog_context()
            pricing_history = await self._build_pricing_history()

            # 2. Build the AI prompt
            context_parts = [catalog]
            if pricing_history:
                context_parts.append(pricing_history)
            context_str = "\n\n".join(context_parts)

            user_prompt = (
                f"## 产品/材质/工艺目录\n\n{context_str}\n\n"
                f"## 客户需求\n\n{description}"
            )

            # 3. Call AI with quote_assist task_code
            response = await self.ai_client.chat_completion(
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=4096,
                task_code="quote_assist",
                temperature=0.3,
            )
            ai_data = self._parse_response(response)

            if not ai_data or not ai_data.get("items"):
                logger.warning("AI returned empty/parsed data, falling back to rule-based")
                return await self._rule_based.compose_draft_quote(description, customer_id)

            # 4. Validate and enrich items
            validated_items = await self._validate_items(ai_data.get("items", []))

            # 5. Get similar historical quotes for reference
            finder = QuoteFinder(self.db)
            keywords = await finder.extract_keywords(description)
            similar_quotes, pricing = await finder.find_similar(
                keyword=" ".join(keywords) if keywords else description,
                limit=3,
            )

            # 6. Calculate confidence
            confidence = self._calc_confidence(ai_data, pricing_history)

            return {
                "project_name": ai_data.get("project_name", "新项目"),
                "items": validated_items,
                "total_estimate": pricing.get("recommended_price", 0) or
                    sum(i.get("unit_price", 0) * i.get("quantity", 1) *
                        max(i.get("width", 1) * i.get("height", 1), 1)
                        for i in validated_items),
                "confidence": confidence,
                "similar_quotes_count": len(similar_quotes),
                "similar_quotes": similar_quotes,
                "ai_analysis": ai_data.get("analysis", ""),
                "risk_notes": ai_data.get("risk_notes", []),
                "pricing_notes": ai_data.get("pricing_notes", ""),
            }

        except (AIClientError, AIAPIError, AIGatewayError) as e:
            logger.warning("AI quote generation failed (%s), falling back to rule-based", str(e)[:100])
            return await self._rule_based.compose_draft_quote(description, customer_id)

    # ── Catalog context ──

    async def _build_catalog_context(self) -> str:
        """Build full catalog summary with product/material/process info."""
        lines: list[str] = []

        # Products
        prod_result = await self.db.execute(
            select(Product).order_by(Product.name)
        )
        products = prod_result.scalars().all()
        if products:
            lines.append("--- 产品 ---")
            for p in products:
                unit_info = f"/{p.unit}" if p.unit else ""
                lines.append(
                    f"- [{p.id}] {p.name}（定价方式: {p.pricing_method or 'area'}"
                    f"，默认价: ¥{float(p.default_price or 0):.2f}{unit_info}"
                    f"{'，需安装' if p.needs_installation else ''}"
                    f"{'，可外协' if p.allows_outsource else ''}）"
                )

        # Materials
        mat_result = await self.db.execute(
            select(Material).order_by(Material.name)
        )
        materials = mat_result.scalars().all()
        if materials:
            lines.append("--- 材质 ---")
            for m in materials:
                unit_info = f"/{m.unit}" if m.unit else ""
                thickness = f"，{m.thickness_mm}mm" if m.thickness_mm else ""
                lines.append(
                    f"- [{m.id}] {m.name}{thickness}"
                    f"（进价: ¥{float(m.purchase_price or 0):.2f}"
                    f"，售价: ¥{float(m.sale_price or 0):.2f}{unit_info}）"
                )

        # Processes
        proc_result = await self.db.execute(
            select(Process).order_by(Process.name)
        )
        processes = proc_result.scalars().all()
        if processes:
            lines.append("--- 工艺 ---")
            for p in processes:
                lines.append(
                    f"- [{p.id}] {p.name}（计费: {p.billing_basis or 'fixed'}"
                    f"，价格: ¥{float(p.default_price or 0):.2f}）"
                )

        return "\n".join(lines) if lines else "暂无产品/材质/工艺数据"

    # ── Historical pricing context ──

    async def _build_pricing_history(self) -> str | None:
        """Build historical pricing summary from past quote items."""
        try:
            # Use raw SQL for efficient aggregation
            rows = await self.db.execute(sa_text("""
                SELECT
                    bi.product_id,
                    p.name AS product_name,
                    COUNT(bi.id) AS cnt,
                    ROUND(AVG(bi.unit_price::numeric), 2) AS avg_price,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY bi.unit_price)::numeric, 2) AS med_price,
                    ROUND(MIN(bi.unit_price::numeric), 2) AS min_price,
                    ROUND(MAX(bi.unit_price::numeric), 2) AS max_price,
                    ROUND(AVG(bi.design_fee::numeric), 0) AS avg_design_fee,
                    ROUND(AVG(bi.installation_fee::numeric), 0) AS avg_install_fee
                FROM business_document_items bi
                JOIN products p ON p.id = bi.product_id
                WHERE bi.unit_price > 0
                GROUP BY bi.product_id, p.name
                HAVING COUNT(bi.id) >= 2
                ORDER BY COUNT(bi.id) DESC
                LIMIT 20
            """))
            history_rows = rows.fetchall()
        except Exception:
            return None

        if not history_rows:
            return None

        lines = ["--- 历史定价参考（基于过去报价数据） ---"]
        for row in history_rows:
            product_id, name, cnt, avg_p, med_p, min_p, max_p, avg_df, avg_if = row
            lines.append(
                f"- {name}（样本数: {cnt}，中位数价: ¥{float(med_p or 0):.2f}"
                f"，均价: ¥{float(avg_p or 0):.2f}"
                f"，区间: ¥{float(min_p or 0):.2f}~¥{float(max_p or 0):.2f}"
                f"，平均设计费: ¥{float(avg_df or 0):.0f}"
                f"，平均安装费: ¥{float(avg_if or 0):.0f}）"
            )

        return "\n".join(lines)

    # ── Response parsing ──

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        # Strip markdown code block markers
        if text.startswith("```"):
            # Find the first and last ```
            start = text.index("\n")
            end = text.rindex("```")
            if start > 0 and end > start:
                text = text[start:end].strip()
            else:
                text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse AI response as JSON: %s", e)
            return {}

    # ── Item validation ──

    async def _validate_items(self, items: list[dict]) -> list[dict]:
        """Validate and normalize AI-generated items."""
        processed = []
        for item in items:
            legacy_length = self._to_float(item.get("length"))
            legacy_width = self._to_float(item.get("width"))
            normalized = {
                "item_name": item.get("item_name", ""),
                "product_id": item.get("product_id"),
                "material_id": item.get("material_id"),
                "material_process": item.get("material_process"),
                "width": legacy_length or legacy_width,
                "height": legacy_width if legacy_length else self._to_float(item.get("height")),
                "quantity": max(1, self._to_float(item.get("quantity", 1))),
                "unit": item.get("unit", "㎡"),
                "unit_price": max(0, self._to_float(item.get("unit_price", 0))),
                "design_fee": max(0, self._to_float(item.get("design_fee", 0))),
                "installation_fee": max(0, self._to_float(item.get("installation_fee", 0))),
                "process_fee": max(0, self._to_float(item.get("process_fee", 0))),
                "transport_fee": max(0, self._to_float(item.get("transport_fee", 0))),
                "other_fee": max(0, self._to_float(item.get("other_fee", 0))),
                "remark": item.get("remark", "") or "",
            }
            # Cross-reference product_id from catalog
            if not normalized["product_id"]:
                matched_id = await self._match_product(normalized["item_name"])
                if matched_id:
                    normalized["product_id"] = str(matched_id)
            if not normalized["material_id"]:
                matched_id = await self._match_material(normalized["item_name"])
                if matched_id:
                    normalized["material_id"] = str(matched_id)
            processed.append(normalized)

        return processed

    @staticmethod
    def _to_float(val: Any) -> float:
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    async def _match_product(self, item_name: str) -> str | None:
        """Try to match an item name to a product by keyword."""
        if not item_name:
            return None
        name_lower = item_name.lower()
        try:
            result = await self.db.execute(
                select(Product).order_by(Product.name)
            )
            for p in result.scalars().all():
                if any(kw in name_lower for kw in p.name.lower().split()):
                    return str(p.id)
        except Exception:
            pass
        return None

    async def _match_material(self, item_name: str) -> str | None:
        """Try to match an item name to a material."""
        if not item_name:
            return None
        name_lower = item_name.lower()
        try:
            result = await self.db.execute(
                select(Material).order_by(Material.name)
            )
            for m in result.scalars().all():
                if m.name.lower() in name_lower:
                    return str(m.id)
        except Exception:
            pass
        return None

    # ── Confidence scoring ──

    @staticmethod
    def _calc_confidence(ai_data: dict, pricing_history: str | None) -> str:
        """Calculate confidence based on data richness."""
        score = 0.5  # base

        items = ai_data.get("items", [])
        if items:
            score += 0.1
            if all(i.get("product_id") for i in items):
                score += 0.1
            if all(i.get("width") and i.get("height") for i in items):
                score += 0.1
            if all(i.get("unit_price", 0) > 0 for i in items):
                score += 0.1

        if pricing_history:
            score += 0.1

        if ai_data.get("project_name"):
            score += 0.05

        if score >= 0.9:
            return "high"
        if score >= 0.6:
            return "medium"
        return "low"


# ── Smart pricing recommendation engine ──

class SmartPricingRecommendation:
    """Generates smart pricing recommendations based on historical data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def recommend_price(
        self,
        product_id: str | None = None,
        material_id: str | None = None,
        width_mm: float | None = None,
        height_mm: float | None = None,
        quantity: float = 1,
    ) -> dict:
        """Recommend a price based on historical data and catalog defaults."""
        default_price = 0.0
        if product_id:
            result = await self.db.execute(
                select(Product).where(Product.id == UUID(product_id))
            )
            prod = result.scalar_one_or_none()
            if prod:
                default_price = float(prod.default_price or 0)

        # Get historical average for this product
        avg_price = None
        if product_id:
            try:
                rows = await self.db.execute(sa_text("""
                    SELECT ROUND(AVG(unit_price::numeric), 2)
                    FROM business_document_items
                    WHERE product_id = :pid AND unit_price > 0 AND deleted_at IS NULL
                """), {"pid": product_id})
                row = rows.fetchone()
                if row and row[0]:
                    avg_price = float(row[0])
            except Exception:
                pass

        recommended = avg_price or default_price
        price_range = {
            "min": round(recommended * 0.8, 2),
            "max": round(recommended * 1.2, 2),
            "recommended": recommended,
        }

        return {
            "default_price": default_price,
            "historical_avg": avg_price,
            "price_range": price_range,
            "confidence": "high" if avg_price else "medium",
        }
