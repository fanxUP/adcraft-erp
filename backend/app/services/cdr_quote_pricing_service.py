"""CDR 智能报价——业务服务层。"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.services.price_engine import (
    PriceEngine, CalculateRequest, CalculateResult,
    ProductInfo, MaterialInfo, ProcessInfo, CustomerAgreement,
)
from app.models.product import Product, Material, Process

from app.services.cdr_quote_base_service import CdrQuoteServiceBase


class CdrQuotePricingService(CdrQuoteServiceBase):
    # ── 报价试算 ──

    async def calculate(self, data: dict) -> dict:
        """执行报价试算（不保存）。"""
        req = await self._build_calculate_request(data)
        result = self.engine.calculate(req)
        return self._result_to_dict(result)

    async def _build_calculate_request(self, data: dict) -> CalculateRequest:
        """从请求数据构建计算请求。"""
        product_id = UUID(data["product_id"])
        product_db = await self.repo.get_product(product_id)
        if not product_db:
            raise ValueError(f"产品不存在: {product_id}")

        product = ProductInfo(
            id=product_db.id,
            pricing_method=product_db.pricing_method,
            default_price=Decimal(str(product_db.default_price or 0)),
            min_charge=Decimal(str(product_db.min_charge or 0)),
            default_loss_rate=Decimal(str(product_db.default_loss_rate or 0)),
            requires_geometry=product_db.requires_geometry,
            needs_installation=product_db.needs_installation,
            allows_outsource=product_db.allows_outsource,
            needs_approval=product_db.needs_approval,
            unit=product_db.unit,
        )

        material: MaterialInfo | None = None
        if material_id := data.get("material_id"):
            mat_db = await self.repo.get_material(UUID(material_id))
            if mat_db:
                material = MaterialInfo(
                    id=mat_db.id,
                    name=mat_db.name,
                    purchase_price=Decimal(str(mat_db.purchase_price or 0)),
                    sale_price=Decimal(str(mat_db.sale_price or 0)),
                    loss_rate=Decimal(str(mat_db.loss_rate or 0)),
                    unit=mat_db.unit,
                    thickness_mm=Decimal(str(mat_db.thickness_mm)) if mat_db.thickness_mm else None,
                    sheet_width_mm=Decimal(str(mat_db.sheet_width_mm)) if mat_db.sheet_width_mm else None,
                    sheet_height_mm=Decimal(str(mat_db.sheet_height_mm)) if mat_db.sheet_height_mm else None,
                )

        processes: list[ProcessInfo] = []
        if process_ids := data.get("process_ids", []):
            procs_db = await self.repo.get_processes([UUID(pid) for pid in process_ids])
            for p in procs_db:
                processes.append(ProcessInfo(
                    id=p.id,
                    name=p.name,
                    billing_basis=p.billing_basis or "fixed",
                    default_price=Decimal(str(p.default_price or 0)),
                    startup_fee=Decimal(str(p.startup_fee or 0)),
                    min_charge=Decimal(str(p.min_charge or 0)),
                    standard_hours=Decimal(str(p.standard_hours)) if p.standard_hours else None,
                ))

        customer_agreement: CustomerAgreement | None = None
        if customer_id := data.get("customer_id"):
            ca = await self.repo.get_customer_agreement(UUID(customer_id), product.id)
            if ca:
                customer_agreement = CustomerAgreement(
                    pricing_method=ca.pricing_method,
                    price_value=Decimal(str(ca.price_value)),
                    minimum_charge=Decimal(str(ca.minimum_charge)),
                    discount_rate=Decimal(str(ca.discount_rate)),
                )

        return CalculateRequest(
            product=product,
            material=material,
            processes=processes,
            customer_agreement=customer_agreement,
            width_mm=Decimal(str(data["width_mm"])) if data.get("width_mm") else None,
            height_mm=Decimal(str(data["height_mm"])) if data.get("height_mm") else None,
            length_m=Decimal(str(data["length_m"])) if data.get("length_m") else None,
            quantity=Decimal(str(data.get("quantity", 1))),
            tax_rate=Decimal(str(data.get("tax_rate", 0))),
            # Phase 7 几何参数
            hole_area_mm2=Decimal(str(data["hole_area_mm2"])) if data.get("hole_area_mm2") else None,
            is_open_curve=bool(data.get("is_open_curve", False)),
            curve_length_mm=Decimal(str(data["curve_length_mm"])) if data.get("curve_length_mm") else None,
            use_sheet_rounding=bool(data.get("use_sheet_rounding", False)),
            sheet_width_mm=Decimal(str(data["sheet_width_mm"])) if data.get("sheet_width_mm") else None,
            sheet_height_mm=Decimal(str(data["sheet_height_mm"])) if data.get("sheet_height_mm") else None,
            sheet_sale_price=Decimal(str(data["sheet_sale_price"])) if data.get("sheet_sale_price") else None,
        )

    def _result_to_dict(self, result: CalculateResult) -> dict:
        return {
            "billable_quantity": str(result.billable_quantity),
            "unit_price": str(result.unit_price),
            "subtotal_amount": str(result.subtotal_amount),
            "material_cost": str(result.material_cost),
            "process_cost": str(result.process_cost),
            "startup_fee": str(result.startup_fee),
            "total_cost": str(result.total_cost),
            "discount_amount": str(result.discount_amount),
            "tax_amount": str(result.tax_amount),
            "total_amount": str(result.total_amount),
            "minimum_charge_applied": result.minimum_charge_applied,
            "requires_approval": result.requires_approval,
            "geometry_estimates": result.geometry_estimates,
            "sheet_usage": result.sheet_usage,
            "warnings": result.warnings,
            "pricing_trace": [
                {"rule_code": s.rule_code, "description": s.description,
                 "input_value": s.input_value, "output_value": s.output_value}
                for s in result.pricing_trace
            ],
        }

    # ── 报价查询 ──

    async def get_quote(self, quote_id: UUID) -> dict | None:
        """获取 CDR 报价 header 信息。"""
        from app.services.business_document_service import BusinessDocumentService
        svc = BusinessDocumentService(self.db, doc_type="quote", quote_mode="cdr")
        quote = await svc.get_by_id(quote_id)
        if quote:
            quote.setdefault("quote_no", quote.get("doc_no", ""))
        return quote

    async def list_quotes(
        self, page: int = 1, page_size: int = 20,
        status: str | None = None, keyword: str | None = None,
    ) -> tuple[list, int]:
        """列出 CDR 报价（复用 BusinessDocumentService 的 quote 查询）。"""
        from app.services.business_document_service import BusinessDocumentService
        svc = BusinessDocumentService(self.db, doc_type="quote", quote_mode="cdr")
        # Reuse the existing list with exclude_status handling
        docs, total = await svc.repo.list_all(
            skip=(page - 1) * page_size, limit=page_size,
            status=status, keyword=keyword,
            exclude_status="converted",
        )
        return [svc._to_summary(d) for d in docs], total

    # ── 报价版本管理 ──

    async def create_quote_version(self, quote_id: UUID, data: dict, created_by: UUID) -> dict:
        """为报价创建新版本（含明细行）。"""
        max_no = await self.repo.get_max_version_no(quote_id)
        version_data = {
            "quote_id": quote_id,
            "version_no": (max_no or 0) + 1,
            "status": "draft",
            "created_by": created_by,
            "notes": data.get("notes"),
        }
        version = await self.repo.create_version(version_data)

        lines_data = data.get("lines", [])
        for i, line_data in enumerate(lines_data):
            line_dict = {
                "version_id": version.id,
                "line_no": i + 1,
                "product_id": UUID(line_data["product_id"]) if line_data.get("product_id") else None,
                "material_id": UUID(line_data["material_id"]) if line_data.get("material_id") else None,
                "description": line_data["description"],
                "width_mm": Decimal(str(line_data["width_mm"])) if line_data.get("width_mm") else None,
                "height_mm": Decimal(str(line_data["height_mm"])) if line_data.get("height_mm") else None,
                "length_m": Decimal(str(line_data["length_m"])) if line_data.get("length_m") else None,
                "quantity": Decimal(str(line_data.get("quantity", 1))),
                "unit": line_data.get("unit"),
                "pieces": Decimal(str(line_data["pieces"])) if line_data.get("pieces") else None,
            }

            # 对每行执行试算
            calc_data = {
                "product_id": str(line_dict["product_id"]) if line_dict["product_id"] else None,
                "material_id": str(line_dict["material_id"]) if line_dict["material_id"] else None,
                "quantity": line_dict["quantity"],
                "width_mm": line_dict["width_mm"],
                "height_mm": line_dict["height_mm"],
                "length_m": line_dict["length_m"],
                "process_ids": [str(p["process_id"]) for p in line_data.get("processes", [])],
            }
            try:
                calc_result = await self.calculate(calc_data)
            except (ValueError, TypeError, KeyError):
                calc_result = self._empty_calc_result()

            line_dict["billable_quantity"] = Decimal(calc_result["billable_quantity"])
            line_dict["unit_price"] = Decimal(calc_result["unit_price"])
            line_dict["amount"] = Decimal(calc_result["subtotal_amount"])
            line_dict["estimated_cost"] = Decimal(calc_result["total_cost"])
            line_dict["pricing_trace_json"] = calc_result.get("pricing_trace")

            # 手工调整
            if "manual_adjustment" in line_data:
                line_dict["manual_adjustment"] = Decimal(str(line_data["manual_adjustment"]))
                line_dict["source"] = "manual"
            if "manual_reason" in line_data:
                line_dict["manual_reason"] = line_data["manual_reason"]
            line_dict["requires_approval"] = calc_result.get("requires_approval", False)

            line = await self.repo.create_line(line_dict)

            # 创建工艺明细
            for proc_data in line_data.get("processes", []):
                await self.repo.create_line_process({
                    "line_id": line.id,
                    "process_id": UUID(proc_data["process_id"]),
                    "billing_quantity": Decimal(str(proc_data.get("billing_quantity", 1))),
                    "unit": proc_data.get("unit"),
                    "unit_price": Decimal(str(proc_data.get("unit_price", 0))),
                    "amount": Decimal(str(proc_data.get("amount", 0))),
                    "cost_amount": Decimal(str(proc_data.get("cost_amount", 0))),
                })

        # 重新计算版本汇总
        await self._recalc_version_totals(version.id)

        # 审计日志
        await self.repo.create_audit_log({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "actor_id": created_by,
            "action": "version.created",
            "after_json": {"version_no": (max_no or 0) + 1, "line_count": len(lines_data)},
        })

        return self._version_to_dict(version)

    async def _recalc_version_totals(self, version_id: UUID) -> None:
        """重新计算版本汇总金额。"""
        version = await self.repo.get_version(version_id)
        if not version:
            return

        subtotal = sum((line.amount or 0) for line in version.lines)
        total_cost = sum((line.estimated_cost or 0) for line in version.lines)

        from sqlalchemy import update as sa_update
        from app.models.cdr_quote import QuoteVersion
        values = {
            "subtotal_amount": subtotal,
            "total_amount": subtotal,
            "estimated_cost": total_cost,
        }
        if total_cost > 0 and subtotal > 0:
            values["estimated_profit"] = subtotal - total_cost
            values["estimated_margin"] = (subtotal - total_cost) / subtotal

        await self.db.execute(
            sa_update(QuoteVersion).where(QuoteVersion.id == version_id).values(**values)
        )
        await self.db.flush()

    def _empty_calc_result(self) -> dict:
        return {
            "billable_quantity": "0",
            "unit_price": "0",
            "subtotal_amount": "0",
            "total_cost": "0",
            "requires_approval": False,
            "warnings": [],
            "pricing_trace": [],
        }

    def _version_to_dict(self, version: Any) -> dict:
        lines = []
        for line in (getattr(version, "lines", []) or []):
            lines.append({
                "id": str(line.id),
                "line_no": line.line_no,
                "product_id": str(line.product_id) if line.product_id else None,
                "description": line.description,
                "width_mm": str(line.width_mm) if line.width_mm else None,
                "height_mm": str(line.height_mm) if line.height_mm else None,
                "length_m": str(line.length_m) if line.length_m else None,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
                "amount": str(line.amount),
                "estimated_cost": str(line.estimated_cost),
                "source": line.source,
                "requires_approval": line.requires_approval,
                "processes": [
                    {
                        "id": str(p.id),
                        "process_id": str(p.process_id),
                        "billing_quantity": str(p.billing_quantity),
                        "unit_price": str(p.unit_price),
                        "amount": str(p.amount),
                    }
                    for p in (getattr(line, "processes", []) or [])
                ],
            })

        return {
            "id": str(version.id),
            "quote_id": str(version.quote_id),
            "version_no": version.version_no,
            "status": version.status,
            "subtotal_amount": str(version.subtotal_amount),
            "total_amount": str(version.total_amount),
            "estimated_cost": str(version.estimated_cost),
            "estimated_profit": str(version.estimated_profit),
            "estimated_margin": str(version.estimated_margin),
            "notes": version.notes,
            "created_by": str(version.created_by) if version.created_by else None,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "lines": lines,
        }

    async def get_latest_version(self, quote_id: UUID) -> dict | None:
        v = await self.repo.get_latest_version(quote_id)
        if v:
            return self._version_to_dict(v)
        return None

    async def list_versions(self, quote_id: UUID) -> list[dict]:
        versions = await self.repo.list_versions(quote_id)
        return [self._version_to_dict(v) for v in versions]
