"""Rule-based quote finder — search historical quotes for similarity and pricing guidance.

Zero AI dependency. Uses SQL ILIKE matching and dimension range filtering.
Also capable of composing a draft quote from natural language descriptions.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote, QuoteItem
from app.models.product import Product, Material, Process


# Chinese stop words for keyword extraction
STOP_WORDS = {
    "的", "了", "是", "在", "和", "与", "或", "要", "做", "含", "面", "一",
    "个", "有", "不", "都", "也", "把", "被", "从", "到", "对", "让", "给",
    "向", "由", "及", "等", "其", "为", "以", "可", "用", "请", "需要",
}


class QuoteFinder:
    """Search historical quotes by keyword, dimensions, and materials.

    Usage:
        finder = QuoteFinder(db)
        similar, pricing = await finder.find_similar("党建文化墙 6m×2m PVC")
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Similar quote search ─────────────────────────────────────────────

    async def find_similar(
        self,
        keyword: str,
        min_area: float | None = None,
        max_area: float | None = None,
        material_ids: list[UUID] | None = None,
        limit: int = 5,
    ) -> tuple[list[dict], dict]:
        """Search confirmed/converted quotes matching the criteria.

        Returns: (list of similar quote dicts, pricing summary dict)
        """
        # Build base query
        query = (
            select(Quote)
            .where(
                Quote.status.in_(["confirmed", "converted"]),
                Quote.deleted_at.is_(None),
            )
        )

        # Keyword filter
        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(
                or_(
                    Quote.project_name.ilike(pattern),
                    Quote.id.in_(
                        select(QuoteItem.quote_id).where(
                            QuoteItem.item_name.ilike(pattern)
                        )
                    ),
                )
            )

        query = query.order_by(Quote.created_at.desc()).limit(limit * 3)

        result = await self.db.execute(query)
        quotes = result.scalars().all()

        # Post-filter by area and material (area requires item aggregation)
        items_data: list[dict] = []
        for quote in quotes:
            total_area = 0.0
            items_summary_parts: list[str] = []
            has_material_match = material_ids is None

            for item in quote.items:
                area = (item.length or 0) * (item.width or 0) * (item.quantity or 1)
                total_area += area
                if item.material_id and material_ids:
                    if item.material_id in material_ids:
                        has_material_match = True
                if item.item_name:
                    items_summary_parts.append(item.item_name)

            if min_area is not None and total_area < min_area:
                continue
            if max_area is not None and total_area > max_area:
                continue
            if not has_material_match:
                continue

            # Calculate profit metrics if available
            gross_profit = float(quote.gross_profit or 0)
            total_amount = float(quote.total_amount or 0)
            profit_margin = gross_profit / total_amount if total_amount > 0 else 0.0

            items_data.append({
                "quote_id": str(quote.id),
                "quote_no": quote.quote_no,
                "project_name": quote.project_name,
                "total_area": round(total_area, 2),
                "items_summary": "，".join(items_summary_parts[:5]),
                "total_amount": total_amount,
                "gross_profit": gross_profit,
                "profit_margin": round(profit_margin, 4),
                "created_at": quote.created_at.isoformat() if quote.created_at else None,
            })

        # Limit results
        items_data = items_data[:limit]

        # Pricing summary
        amounts = [d["total_amount"] for d in items_data if d["total_amount"] > 0]
        margins = [d["profit_margin"] for d in items_data if d["profit_margin"] > 0]

        pricing_summary = {
            "price_range": [min(amounts), max(amounts)] if amounts else [0, 0],
            "avg_price": round(sum(amounts) / len(amounts), 2) if amounts else 0,
            "avg_margin": round(sum(margins) / len(margins), 4) if margins else 0,
            "recommended_price": round(sum(amounts) / len(amounts), 2) if amounts else 0,
        }

        return items_data, pricing_summary

    # ── Keyword extraction ───────────────────────────────────────────────

    async def extract_keywords(self, description: str) -> list[str]:
        """Extract meaningful keywords from a natural language description.

        Simple approach: split by common delimiters, remove stop words,
        match against product/material names in the catalog.
        """
        # Normalize
        import re

        text = description.replace("×", " ").replace("*", " ").replace("，", " ")
        text = text.replace("、", " ").replace("。", " ").replace("含", " ")

        # Split and clean
        words = re.split(r"[\s,，、。]+", text)
        candidates = [w.strip() for w in words if len(w.strip()) >= 2 and w.strip() not in STOP_WORDS]

        if not candidates:
            return []

        # Match against catalog
        matched: set[str] = set()

        # Product names
        prod_result = await self.db.execute(
            select(Product.name).where(
                or_(*[Product.name.ilike(f"%{c}%") for c in candidates])
            )
        )
        for name in prod_result.scalars().all():
            matched.add(name)

        # Material names
        mat_result = await self.db.execute(
            select(Material.name).where(
                or_(*[Material.name.ilike(f"%{c}%") for c in candidates])
            )
        )
        for name in mat_result.scalars().all():
            matched.add(name)

        # Process names
        proc_result = await self.db.execute(
            select(Process.name).where(
                or_(*[Process.name.ilike(f"%{c}%") for c in candidates])
            )
        )
        for name in proc_result.scalars().all():
            matched.add(name)

        # Build keyword list: catalog matches first, then original candidates
        keywords = list(matched)
        for c in candidates:
            if c not in keywords:
                keywords.append(c)

        return keywords[:10]

    # ── Draft quote composition ──────────────────────────────────────────

    async def generate_quote_draft(
        self, description: str, customer_id: str | None = None
    ) -> dict:
        """Alias for compose_draft_quote — matches the LLMQuoteAssistant interface."""
        return await self.compose_draft_quote(description, customer_id)

    async def compose_draft_quote(
        self, description: str, customer_id: str | None = None
    ) -> dict:
        """Compose a draft quote from NL description using historical data + catalog.

        This is the rule-based version — returns structured draft items based
        on matching products/materials and similar historical quotes.
        """
        keywords = await self.extract_keywords(description)
        similar_quotes, pricing_summary = await self.find_similar(
            keyword=" ".join(keywords) if keywords else description,
            limit=5,
        )

        # Build draft items from catalog matches
        draft_items: list[dict] = []
        seen_product_ids: set[str] = set()

        for kw in keywords[:5]:
            # Find matching products
            prod_result = await self.db.execute(
                select(Product).where(
                    Product.name.ilike(f"%{kw}%"),
                ).limit(2)
            )
            for product in prod_result.scalars().all():
                pid = str(product.id)
                if pid in seen_product_ids:
                    continue
                seen_product_ids.add(pid)

                item = {
                    "item_name": product.name,
                    "length": None,
                    "width": None,
                    "height": None,
                    "quantity": 1,
                    "unit": "㎡",
                    "product_id": pid,
                    "material_id": None,
                    "process_id": None,
                    "unit_price": float(product.default_price or 0),
                    "design_fee": 0,
                    "installation_fee": 0,
                    "process_fee": 0,
                    "transport_fee": 0,
                    "other_fee": 0,
                    "subtotal": 0,
                    "remark": "",
                }
                draft_items.append(item)

            # Find matching materials
            mat_result = await self.db.execute(
                select(Material).where(
                    Material.name.ilike(f"%{kw}%"),
                ).limit(2)
            )
            for material in mat_result.scalars().all():
                mid = str(material.id)
                if len(draft_items) > 0:
                    draft_items[-1]["material_id"] = mid
                    draft_items[-1]["unit_price"] = float(material.sale_price or 0)

        # If catalog didn't match, create a single generic item from the description
        if not draft_items:
            draft_items.append({
                "item_name": description[:100],
                "length": None,
                "width": None,
                "height": None,
                "quantity": 1,
                "unit": "㎡",
                "product_id": None,
                "material_id": None,
                "process_id": None,
                "unit_price": 0,
                "design_fee": 0,
                "installation_fee": 0,
                "process_fee": 0,
                "transport_fee": 0,
                "other_fee": 0,
                "subtotal": 0,
                "remark": "请手动补充产品/材质信息",
            })

        total_estimate = pricing_summary.get("recommended_price", 0)

        return {
            "project_name": keywords[0] if keywords else "新项目",
            "items": draft_items,
            "total_estimate": total_estimate,
            "confidence": "medium" if similar_quotes else "low",
            "similar_quotes_count": len(similar_quotes),
            "similar_quotes": similar_quotes,
            "ai_analysis": "",
            "risk_notes": [],
        }
