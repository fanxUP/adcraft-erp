"""CDR-specific price anomaly detector — uses geometry data and historical averages.

Extends the system-level AnomalyDetector with CDR-specific rules:
1. Compare unit price per area against historical averages for similar products
2. Flag items >30% deviation from historical norm
3. Detect when geometry net_area differs significantly from bounding_box area
4. Flag when material cost seems misaligned with sheet utilization

Zero AI dependency — statistical rule-based.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdr_quote import (
    QuoteLine, QuoteVersion, QuoteGeometry,
)
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.product import Product

PriceAnomaly = dict[str, Any]


class CdrPriceAnomalyDetector:
    """Detects pricing anomalies in CDR quotes using statistical rules.

    Usage:
        detector = CdrPriceAnomalyDetector(db)
        anomalies = await detector.check_quote(quote_id)
        # or check a single calculation:
        anomalies = await detector.check_calculation(data)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_quote(
        self, quote_id: UUID, version_id: UUID | None = None
    ) -> list[PriceAnomaly]:
        """Run all CDR anomaly checks for a quote."""
        anomalies: list[PriceAnomaly] = []

        # Get version
        if not version_id:
            r = await self.db.execute(
                select(QuoteVersion)
                .where(QuoteVersion.quote_id == quote_id)
                .order_by(QuoteVersion.version_no.desc()).limit(1)
            )
            version = r.scalar_one_or_none()
            if not version:
                return []
            version_id = version.id

        # Load lines
        r_lines = await self.db.execute(
            select(QuoteLine).where(QuoteLine.version_id == version_id)
        )
        lines = r_lines.scalars().all()

        for line in lines:
            # 1. Check unit price per area vs historical
            line_anomalies = await self._check_unit_price_anomaly(line)
            anomalies.extend(line_anomalies)

            # 2. Check geometry-based anomalies
            geo_anomalies = await self._check_geometry_anomaly(line.id, line)
            anomalies.extend(geo_anomalies)

            # 3. Check margin anomalies
            margin_anomalies = self._check_margin_anomaly(line)
            anomalies.extend(margin_anomalies)

        # 4. Check total profit margin
        if lines:
            total_margin = await self._check_total_margin(lines, version)
            if total_margin:
                anomalies.append(total_margin)

        return anomalies

    async def check_calculation(self, data: dict) -> list[PriceAnomaly]:
        """Check a single pricing calculation for anomalies (no DB dependency for basic checks)."""
        anomalies: list[PriceAnomaly] = []

        width = data.get("width_mm")
        height = data.get("height_mm")
        hole_area = data.get("hole_area_mm2")
        unit_price = data.get("unit_price")
        quantity = data.get("quantity", 1)

        # Check hole ratio
        if width and height and hole_area:
            bbox_area = Decimal(str(width)) * Decimal(str(height))
            if bbox_area > 0:
                hole_ratio = Decimal(str(hole_area)) / bbox_area
                if hole_ratio > Decimal("0.3"):
                    anomalies.append({
                        "type": "high_hole_ratio",
                        "severity": "info",
                        "line_no": data.get("line_no"),
                        "title": "孔洞比例超过30%",
                        "detail": f"孔洞面积 {float(hole_area):.0f}mm² vs 包围盒 {float(bbox_area):.0f}mm²（占比 {float(hole_ratio)*100:.1f}%），建议确认是否按净面积计价",
                        "suggestion": "考虑使用孔洞扣除定价策略，避免客户承担过多材料浪费",
                    })

        width_str = str(data.get("width_mm", 0))
        height_str = str(data.get("height_mm", 0))
        unit_price_val = data.get("unit_price", 0)

        return anomalies

    # ── Internal checks ─────────────────────────────────────────

    async def _check_unit_price_anomaly(self, line: QuoteLine) -> list[PriceAnomaly]:
        """Check if unit price deviates from historical averages."""
        anomalies: list[PriceAnomaly] = []

        if not line.unit_price or float(line.unit_price) <= 0:
            return anomalies

        # Get historical prices for same product
        if not line.product_id:
            return anomalies

        # Build criteria for similar items
        area = self._calc_line_area(line)
        if area <= 0:
            return anomalies

        unit_price_per_area = float(line.unit_price) / area

        # Get historical data: other quotes with same product (last 100)
        r = await self.db.execute(
            select(QuoteLine.unit_price, QuoteLine.width_mm, QuoteLine.height_mm, QuoteLine.quantity)
            .where(
                QuoteLine.product_id == line.product_id,
                QuoteLine.id != line.id,
                QuoteLine.unit_price > 0,
                QuoteLine.width_mm.isnot(None),
                QuoteLine.height_mm.isnot(None),
            )
            .order_by(QuoteLine.created_at.desc())
            .limit(100)
        )
        historical = r.all()

        if not historical:
            return anomalies

        # Calculate historical unit price per area
        hist_prices: list[float] = []
        for h in historical:
            h_area = (float(h.width_mm or 0) * float(h.height_mm or 0) * float(h.quantity or 1)) / 1_000_000
            if h_area > 0:
                hist_prices.append(float(h.unit_price) / h_area)

        if not hist_prices:
            return anomalies

        avg_price = sum(hist_prices) / len(hist_prices)
        std_dev = (sum((p - avg_price) ** 2 for p in hist_prices) / len(hist_prices)) ** 0.5

        # Check deviation
        if avg_price > 0 and std_dev > 0:
            deviation = (unit_price_per_area - avg_price) / std_dev
            deviation_pct = (unit_price_per_area - avg_price) / avg_price * 100

            if abs(deviation_pct) > 50:
                direction = "偏高" if deviation_pct > 0 else "偏低"
                anomalies.append({
                    "type": "price_deviation",
                    "severity": "warning" if abs(deviation_pct) > 80 else "info",
                    "line_no": line.line_no,
                    "title": f"单价{direction}（偏离历史均值 {deviation_pct:.0f}%）",
                    "detail": (
                        f"当前单价 ¥{float(line.unit_price):.2f}（{unit_price_per_area:.2f}/㎡），"
                        f"历史均值 ¥{avg_price:.2f}/㎡（基于 {len(hist_prices)} 条历史数据）"
                    ),
                    "suggestion": (
                        "建议检查定价策略，确认是否因材质变更、加工复杂度或客户特殊情况导致偏差"
                        if abs(deviation_pct) > 80 else
                        "偏差在可接受范围内，建议复核以确保合理"
                    ),
                    "current_price": float(line.unit_price),
                    "historical_avg": round(avg_price, 2),
                    "deviation_pct": round(deviation_pct, 1),
                })

        return anomalies

    async def _check_geometry_anomaly(
        self, line_id: UUID, line: QuoteLine
    ) -> list[PriceAnomaly]:
        """Check geometry-based pricing anomalies."""
        anomalies: list[PriceAnomaly] = []

        # Get geometry data
        r = await self.db.execute(
            select(QuoteGeometry).where(QuoteGeometry.quote_line_id == line_id)
        )
        geo = r.scalar_one_or_none()
        if not geo:
            return anomalies

        # Check hole ratio significance
        if geo.hole_area_mm2 and geo.net_area_mm2 and geo.net_area_mm2 > 0:
            total_with_holes = float(geo.hole_area_mm2) + float(geo.net_area_mm2)
            if total_with_holes > 0:
                hole_ratio = float(geo.hole_area_mm2) / total_with_holes
                if hole_ratio > 0.3:
                    anomalies.append({
                        "type": "geometry_hole_ratio",
                        "severity": "info",
                        "line_no": line.line_no,
                        "title": "异形件孔洞比例较高",
                        "detail": f"孔洞占比 {hole_ratio*100:.1f}%，建议按净面积计费",
                        "suggestion": "在报价计算中启用 hole_area_mm2 参数扣除孔洞面积",
                    })

        # Check sheet utilization
        if geo.sheet_utilization_pct and geo.sheet_utilization_pct < 30:
            anomalies.append({
                "type": "low_sheet_utilization",
                "severity": "info",
                "line_no": line.line_no,
                "title": "板材利用率过低",
                "detail": f"利用率仅 {float(geo.sheet_utilization_pct):.1f}%，可能有大量边角料浪费",
                "suggestion": "考虑与其他订单合并排版以提高利用率，或选择更合适的板材规格",
            })

        # Check overlap detected
        if geo.overlap_count and geo.overlap_count > 0:
            anomalies.append({
                "type": "overlap_detected",
                "severity": "warning",
                "line_no": line.line_no,
                "title": "检测到图形重叠",
                "detail": f"发现 {geo.overlap_count} 处重叠，可能导致面积计算偏大",
                "suggestion": "建议检查 CDR 源文件中的重叠对象，修正后再报价",
            })

        return anomalies

    @staticmethod
    def _check_margin_anomaly(line: QuoteLine) -> list[PriceAnomaly]:
        """Check if estimated profit margin flags issues."""
        anomalies: list[PriceAnomaly] = []

        if float(line.estimated_cost or 0) <= 0 or float(line.amount or 0) <= 0:
            return anomalies

        margin = (float(line.amount) - float(line.estimated_cost)) / float(line.amount)

        if margin < 0.05:
            anomalies.append({
                "type": "low_margin",
                "severity": "critical" if margin < 0 else "warning",
                "line_no": line.line_no,
                "title": "利润率过低" if margin >= 0 else "可能亏损",
                "detail": f"第{line.line_no}项「{line.description}」利润率 {margin*100:.1f}%",
                "suggestion": "检查成本核算是否准确，考虑优化工艺或调整报价",
                "margin_pct": round(margin * 100, 1),
            })
        elif margin > 0.6:
            anomalies.append({
                "type": "high_margin",
                "severity": "info",
                "line_no": line.line_no,
                "title": "利润率偏高",
                "detail": f"第{line.line_no}项「{line.description}」利润率 {margin*100:.1f}%，可能高于市场平均水平",
                "suggestion": "确认客户是否接受此价格，或检查成本是否被高估",
                "margin_pct": round(margin * 100, 1),
            })

        return anomalies

    async def _check_total_margin(self, lines: list, version) -> list[PriceAnomaly]:
        """Check total profit margin of the quote."""
        anomalies: list[PriceAnomaly] = []

        total_amount = sum(float(l.amount or 0) for l in lines)
        total_cost = sum(float(l.estimated_cost or 0) for l in lines)

        if total_amount <= 0:
            return anomalies

        margin = (total_amount - total_cost) / total_amount if total_amount > 0 else 0

        if margin < 0.08:
            anomalies.append({
                "type": "total_low_margin",
                "severity": "critical" if margin < 0 else "warning",
                "line_no": 0,
                "title": f"整体利润率{'亏损' if margin < 0 else '偏低'}",
                "detail": f"报价总金额 ¥{total_amount:,.2f}，总成本 ¥{total_cost:,.2f}，利润率 {margin*100:.1f}%",
                "suggestion": "建议增加高毛利项目以平衡整体利润",
                "margin_pct": round(margin * 100, 1),
            })
        elif margin > 0.5:
            anomalies.append({
                "type": "total_high_margin",
                "severity": "info",
                "line_no": 0,
                "title": "整体利润率偏高",
                "detail": f"报价总金额 ¥{total_amount:,.2f}，总成本 ¥{total_cost:,.2f}，利润率 {margin*100:.1f}%",
                "suggestion": "确认报价是否具有竞争力，与历史同类报价对比",
                "margin_pct": round(margin * 100, 1),
            })

        return anomalies

    @staticmethod
    def _calc_line_area(line: QuoteLine) -> float:
        """Calculate line area in m²."""
        w = float(line.width_mm or 0)
        h = float(line.height_mm or 0)
        qty = float(line.quantity or 1)
        if w > 0 and h > 0:
            return (w * h * qty) / 1_000_000
        return 0
