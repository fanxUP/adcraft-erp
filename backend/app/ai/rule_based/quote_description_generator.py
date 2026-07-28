"""Quote description generator — auto-generates Chinese quote descriptions from items.

Template-driven, no AI dependency, always available.

Generates:
1. Project overview paragraph
2. Item-by-item breakdown table (text)
3. Production and delivery terms
4. Payment terms (from customer data)
5. Validity and warranty terms
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdr_quote import QuoteLine, QuoteVersion, QuoteLineProcess
from app.models.customer import Customer

# ── Template sections ──────────────────────────────────────────

PROJECT_OVERVIEW_TPL = (
    "项目名称：{project_name}\n"
    "报价编号：{quote_no}\n"
    "报价日期：{quote_date}\n"
    "有效期至：{valid_until}\n"
    "客户名称：{customer_name}\n\n"
)

ITEM_BREAKDOWN_HEADER = "一、报价明细\n\n"

ITEM_LINE_TPL = (
    "{line_no}. {description}\n"
    "   规格：{dimensions}\n"
    "   数量：{quantity} {unit}\n"
    "   单价：¥{unit_price:,.2f}\n"
    "   金额：¥{amount:,.2f}\n"
    "   工艺：{processes}\n"
)

TERMS_PAYMENT_TPL = (
    "二、付款方式\n\n"
    "1. 预付款：合同签订后支付合同总金额的 {deposit_pct}% 作为定金；\n"
    "2. 尾款：{payment_terms}\n"
    "3. 付款方式：支持银行转账、微信、支付宝等方式。\n\n"
)

TERMS_DELIVERY_TPL = (
    "三、交货与安装\n\n"
    "1. 交货地点：{delivery_address}\n"
    "2. 交货期限：合同签订后 {lead_days} 个工作日内完成制作{install_suffix}\n"
    "3. 运输方式：由{transport_responsibility}负责运输\n\n"
)

TERMS_WARRANTY_TPL = (
    "四、质量保证\n\n"
    "1. 质保期：{warranty_months}个月（自验收合格之日起算）；\n"
    "2. 质保期内因工艺质量问题免费维修；\n"
    "3. 因使用不当或人为损坏不在质保范围内；\n"
    "4. 超出质保范围或质保期的维修，按实际成本收费。\n\n"
)

TERMS_OTHER_TPL = (
    "五、其他约定\n\n"
    "1. 本报价不含税票，如需开票加收 {tax_rate}% 税费；\n"
    "2. 报价有效期至 {valid_until}，逾期需重新核价；\n"
    "3. 如因客户原因导致方案变更，制作周期和费用相应调整；\n"
    "4. 户外安装涉及高空作业的，需客户配合提供作业条件。\n"
)

TERMS_OTHER_NO_TAX_TPL = (
    "五、其他约定\n\n"
    "1. 本报价含税（税率 {tax_rate}%），可开具增值税发票；\n"
    "2. 报价有效期至 {valid_until}，逾期需重新核价；\n"
    "3. 如因客户原因导致方案变更，制作周期和费用相应调整；\n"
    "4. 户外安装涉及高空作业的，需客户配合提供作业条件。\n"
)

# ── Default values ─────────────────────────────────────────────

DEFAULT_LEAD_DAYS = 7
DEFAULT_WARRANTY_MONTHS = 12
DEFAULT_DEPOSIT_PCT = 50
DEFAULT_PAYMENT_TERMS = "货到安装验收合格后付清尾款"
DEFAULT_DELIVERY_ADDRESS = "双方协商确定"
DEFAULT_TRANSPORT = "供方"


def _format_dimensions(line: QuoteLine) -> str:
    parts = []
    if line.width_mm:
        parts.append(f"宽{float(line.width_mm):.0f}mm")
    if line.height_mm:
        parts.append(f"高{float(line.height_mm):.0f}mm")
    if line.length_m:
        parts.append(f"长{float(line.length_m):.1f}m")
    if not parts:
        return "按实际尺寸"
    return "×".join(parts)


def _format_processes(line: QuoteLine) -> str:
    if not line.processes:
        return "标准制作"
    names = []
    # We'd need process names — for now just return placeholders
    return "、".join([f"工艺#{p.process_id}" for p in line.processes]) or "标准制作"


class QuoteDescriptionGenerator:
    """Generates structured Chinese quote descriptions.

    Usage:
        gen = QuoteDescriptionGenerator(db)
        result = await gen.generate(quote_id)
        # result["description"] — full text
        # result["sections"] — individual sections
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self,
        quote_id: UUID,
        version_id: UUID | None = None,
        customer_id: UUID | None = None,
        options: dict | None = None,
    ) -> dict[str, Any]:
        """Generate a full quote description.

        Args:
            quote_id: 报价ID
            version_id: 版本ID（默认最新版本）
            customer_id: 客户ID（用于获取付款条款）
            options: 覆盖默认值的选项
                - lead_days: 交期天数
                - warranty_months: 质保月数
                - deposit_pct: 定金比例
                - payment_terms: 付款条件
                - delivery_address: 交货地址
                - transport_responsibility: 运输责任
                - tax_rate: 税率
                - valid_until: 有效期
        """
        opts = options or {}

        # Get latest version
        if not version_id:
            r = await self.db.execute(
                select(QuoteVersion)
                .where(QuoteVersion.quote_id == quote_id)
                .order_by(QuoteVersion.version_no.desc()).limit(1)
            )
            version = r.scalar_one_or_none()
            if not version:
                return {"error": "报价没有版本数据"}
        else:
            r = await self.db.execute(
                select(QuoteVersion).where(QuoteVersion.id == version_id)
            )
            version = r.scalar_one_or_none()
            if not version:
                return {"error": "版本不存在"}

        # Get quote header via SQL
        from app.models.business_document import BusinessDocument
        r_q = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id == quote_id)
        )
        quote_doc = r_q.scalar_one_or_none()
        if not quote_doc:
            return {"error": "报价不存在"}

        # Get customer info
        customer_info = {}
        if customer_id:
            r_c = await self.db.execute(
                select(Customer).where(Customer.id == customer_id)
            )
            customer = r_c.scalar_one_or_none()
            if customer:
                customer_info = {
                    "payment_days": customer.default_payment_days,
                    "credit_limit": float(customer.credit_limit or 0),
                }

        # Load lines
        r_lines = await self.db.execute(
            select(QuoteLine)
            .where(QuoteLine.version_id == version.id)
            .order_by(QuoteLine.line_no)
        )
        lines = r_lines.scalars().all()

        # Build sections
        sections = {
            "project_overview": self._build_project_overview(
                quote_doc, version, opts
            ),
            "item_breakdown": self._build_item_breakdown(lines),
            "payment_terms": self._build_payment_terms(customer_info, opts),
            "delivery_terms": self._build_delivery_terms(opts),
            "warranty_terms": self._build_warranty_terms(opts),
            "other_terms": self._build_other_terms(opts),
        }

        # Summary statistics
        total_amount = float(version.total_amount or 0)
        total_items = len(lines)
        tax_rate = opts.get("tax_rate", float(version.tax_rate or 0) * 100)

        return {
            "description": "\n".join(v for v in sections.values() if v),
            "sections": sections,
            "summary": {
                "total_amount": total_amount,
                "total_items": total_items,
                "tax_rate": tax_rate,
            },
        }

    # ── Section builders ─────────────────────────────────────────

    def _build_project_overview(self, quote_doc, version, opts) -> str:
        """Build project overview section."""
        today = date.today()
        valid_days = opts.get("valid_days", 15)
        valid_until = opts.get("valid_until", (today + timedelta(days=valid_days)).isoformat())
        quote_date = opts.get("quote_date", today.isoformat())

        return PROJECT_OVERVIEW_TPL.format(
            project_name=quote_doc.project_name or "未命名项目",
            quote_no=quote_doc.doc_no or "待编号",
            quote_date=quote_date,
            valid_until=valid_until,
            customer_name=quote_doc.customer_name or "未指定客户",
        )

    def _build_item_breakdown(self, lines: list) -> str:
        """Build item-by-item breakdown."""
        if not lines:
            return ""

        text = ITEM_BREAKDOWN_HEADER
        for line in lines:
            processes = _format_processes(line)
            text += ITEM_LINE_TPL.format(
                line_no=line.line_no,
                description=line.description,
                dimensions=_format_dimensions(line),
                quantity=float(line.quantity),
                unit=line.unit or "个",
                unit_price=float(line.unit_price or 0),
                amount=float(line.amount or 0),
                processes=processes,
            )

        # Total
        total = sum(float(line.amount or 0) for line in lines)
        text += f"\n报价合计：¥{total:,.2f}\n\n"

        return text

    def _build_payment_terms(self, customer_info: dict, opts: dict) -> str:
        """Build payment terms section."""
        deposit_pct = opts.get("deposit_pct", DEFAULT_DEPOSIT_PCT)
        payment_days = customer_info.get("payment_days", 0)
        if payment_days > 0:
            payment_terms = opts.get(
                "payment_terms",
                f"验收合格后 {payment_days} 日内付清尾款",
            )
        else:
            payment_terms = opts.get("payment_terms", DEFAULT_PAYMENT_TERMS)

        return TERMS_PAYMENT_TPL.format(
            deposit_pct=deposit_pct,
            payment_terms=payment_terms,
        )

    def _build_delivery_terms(self, opts: dict) -> str:
        """Build delivery/installation terms."""
        lead_days = opts.get("lead_days", DEFAULT_LEAD_DAYS)
        needs_install = opts.get("needs_installation", True)
        install_suffix = "（含安装）" if needs_install else ""
        delivery_address = opts.get("delivery_address", DEFAULT_DELIVERY_ADDRESS)
        transport = opts.get("transport_responsibility", DEFAULT_TRANSPORT)

        return TERMS_DELIVERY_TPL.format(
            delivery_address=delivery_address,
            lead_days=lead_days,
            install_suffix=install_suffix,
            transport_responsibility=transport,
        )

    def _build_warranty_terms(self, opts: dict) -> str:
        """Build warranty/quality terms."""
        warranty_months = opts.get("warranty_months", DEFAULT_WARRANTY_MONTHS)
        return TERMS_WARRANTY_TPL.format(warranty_months=warranty_months)

    def _build_other_terms(self, opts: dict) -> str:
        """Build other terms (tax, validity, etc.)."""
        tax_rate = opts.get("tax_rate", 0)
        valid_until = opts.get("valid_until")

        if not valid_until:
            valid_until = (date.today() + timedelta(days=15)).isoformat()

        if tax_rate > 0:
            return TERMS_OTHER_NO_TAX_TPL.format(
                tax_rate=tax_rate,
                valid_until=valid_until,
            )
        else:
            return TERMS_OTHER_TPL.format(
                tax_rate=tax_rate,
                valid_until=valid_until,
            )
