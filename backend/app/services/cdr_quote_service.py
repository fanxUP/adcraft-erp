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


class CdrQuoteService:
    """CDR 报价服务——整合报价引擎和数据持久化。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CdrQuoteRepository(db)
        self.engine = PriceEngine()

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

    # ── 审批 ──

    async def request_approval(self, quote_id: UUID, data: dict, requested_by: UUID) -> dict:
        """请求审批。"""
        version = await self.repo.get_latest_version(quote_id)
        if not version:
            raise ValueError("报价没有版本")

        approval = await self.repo.create_approval({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "approval_type": data.get("approval_type", "price_override"),
            "requested_by": requested_by,
            "status": "pending",
            "reason": data.get("reason"),
        })

        if version.status == "draft":
            await self.repo.update_version_status(version.id, "review")

        await self.repo.create_audit_log({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "actor_id": requested_by,
            "action": "approval.requested",
            "after_json": {"approval_type": data.get("approval_type")},
        })

        return {
            "id": str(approval.id),
            "status": "pending",
            "approval_type": approval.approval_type,
            "reason": approval.reason,
        }

    async def approve(self, approval_id: UUID, approver_id: UUID, comment: str | None = None) -> dict:
        """批准报价。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        r = await self.db.execute(select(QuoteApproval).where(QuoteApproval.id == approval_id))
        approval = r.scalar_one_or_none()
        if not approval:
            raise ValueError("审批记录不存在")

        await self.repo.update_approval(approval_id, {
            "status": "approved",
            "approver_id": approver_id,
            "decision_comment": comment,
            "decided_at": datetime.utcnow(),
        })
        if approval.quote_version_id:
            await self.repo.update_version_status(approval.quote_version_id, "approved")

        await self.repo.create_audit_log({
            "quote_id": approval.quote_id,
            "quote_version_id": approval.quote_version_id,
            "actor_id": approver_id,
            "action": "approval.approved",
            "after_json": {"comment": comment},
        })

        return {"status": "approved"}

    async def reject(self, approval_id: UUID, approver_id: UUID, comment: str | None = None) -> dict:
        """驳回报价。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        r = await self.db.execute(select(QuoteApproval).where(QuoteApproval.id == approval_id))
        approval = r.scalar_one_or_none()
        if not approval:
            raise ValueError("审批记录不存在")

        await self.repo.update_approval(approval_id, {
            "status": "rejected",
            "approver_id": approver_id,
            "decision_comment": comment,
            "decided_at": datetime.utcnow(),
        })

        await self.repo.create_audit_log({
            "quote_id": approval.quote_id,
            "quote_version_id": approval.quote_version_id,
            "actor_id": approver_id,
            "action": "approval.rejected",
            "after_json": {"comment": comment},
        })

        return {"status": "rejected"}

    async def list_approvals(self, quote_id: UUID) -> list[dict]:
        """获取报价审批记录列表。"""
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteApproval
        from app.models.user import User
        r = await self.db.execute(
            select(QuoteApproval)
            .where(QuoteApproval.quote_id == quote_id)
            .order_by(QuoteApproval.created_at.desc())
        )
        approvals = r.scalars().all()
        return [{
            "id": str(a.id),
            "quote_id": str(a.quote_id),
            "quote_version_id": str(a.quote_version_id) if a.quote_version_id else None,
            "approval_type": a.approval_type,
            "status": a.status,
            "reason": a.reason,
            "decision_comment": a.decision_comment,
            "requested_by": str(a.requested_by) if a.requested_by else None,
            "approver_id": str(a.approver_id) if a.approver_id else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
        } for a in approvals]

    # ── 规则集 ──

    async def list_rule_sets(self) -> list[dict]:
        rule_sets = await self.repo.list_rule_sets()
        return [{
            "id": str(rs.id),
            "code": rs.code,
            "name": rs.name,
            "version": rs.version,
            "status": rs.status,
            "effective_from": rs.effective_from,
            "effective_to": rs.effective_to,
            "description": rs.description,
        } for rs in rule_sets]

    async def create_rule_set(self, data: dict, published_by: UUID) -> dict:
        rules_data = data.pop("rules", [])
        rs = await self.repo.create_rule_set({
            "code": data["code"],
            "name": data["name"],
            "effective_from": data.get("effective_from"),
            "effective_to": data.get("effective_to"),
            "description": data.get("description"),
            "published_by": published_by,
        })
        for rule_data in rules_data:
            from app.models.cdr_quote import CdrPriceRule
            rule = CdrPriceRule(
                rule_set_id=rs.id,
                code=rule_data["code"],
                name=rule_data["name"],
                priority=rule_data.get("priority", 0),
                conditions_json=rule_data.get("conditions_json", {}),
                actions_json=rule_data.get("actions_json", {}),
                conflict_policy=rule_data.get("conflict_policy", "higher_priority_wins"),
            )
            self.db.add(rule)
        await self.db.flush()
        return {"id": str(rs.id), "code": rs.code, "name": rs.name}

    # ── 客户协议价 ──

    async def list_customer_agreements(self, customer_id: UUID | None = None) -> list[dict]:
        agreements = await self.repo.list_customer_agreements(customer_id)
        return [{
            "id": str(ca.id),
            "customer_id": str(ca.customer_id),
            "product_id": str(ca.product_id) if ca.product_id else None,
            "pricing_method": ca.pricing_method,
            "price_value": str(ca.price_value),
            "minimum_charge": str(ca.minimum_charge),
            "discount_rate": str(ca.discount_rate),
            "effective_from": ca.effective_from,
            "effective_to": ca.effective_to,
            "remark": ca.remark,
        } for ca in agreements]

    async def create_customer_agreement(self, data: dict, approved_by: UUID) -> dict:
        ca = await self.repo.create_customer_agreement({
            "customer_id": UUID(data["customer_id"]),
            "product_id": UUID(data["product_id"]) if data.get("product_id") else None,
            "material_id": UUID(data["material_id"]) if data.get("material_id") else None,
            "process_id": UUID(data["process_id"]) if data.get("process_id") else None,
            "pricing_method": data["pricing_method"],
            "price_value": Decimal(str(data["price_value"])),
            "minimum_charge": Decimal(str(data.get("minimum_charge", 0))),
            "discount_rate": Decimal(str(data.get("discount_rate", 1))),
            "effective_from": data["effective_from"],
            "effective_to": data.get("effective_to"),
            "remark": data.get("remark"),
            "approved_by": approved_by,
        })
        return {"id": str(ca.id), "customer_id": str(ca.customer_id)}

    # ── 转订单 ──

    async def convert_to_order(self, quote_id: UUID, current_user_id: UUID) -> dict:
        """将CDR智能报价转为销售订单，含生产/安装/车辆/外协/财务联动（阶段6）。"""
        from datetime import datetime
        import uuid
        from sqlalchemy import select, update as sa_update
        from app.models.business_document import (
            BusinessDocument, BusinessDocumentItem, BusinessDocumentStatusLog,
        )
        from app.services.number_generator import generate_order_no

        # 1. 获取报价 header
        r = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == quote_id,
                BusinessDocument.doc_type == "quote",
                BusinessDocument.quote_mode == "cdr",
                BusinessDocument.deleted_at.is_(None),
            )
        )
        quote_doc = r.scalar_one_or_none()
        if not quote_doc:
            raise ValueError("报价不存在")

        # 2. 获取最新版本
        version = await self.repo.get_latest_version(quote_id)
        if not version:
            raise ValueError("报价没有版本数据，无法转订单")

        # 3. 检查是否已转换（幂等性验证）
        if quote_doc.status == "converted":
            r2 = await self.db.execute(
                select(BusinessDocument).where(
                    BusinessDocument.source_quote_id == quote_id,
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.deleted_at.is_(None),
                ).order_by(BusinessDocument.created_at.desc()).limit(1)
            )
            existing = r2.scalar_one_or_none()
            if existing:
                return {
                    "id": str(existing.id),
                    "doc_no": existing.doc_no,
                    "project_name": existing.project_name,
                    "total_amount": float(existing.total_amount),
                    "status": existing.status,
                    "note": "该报价已转换过，返回现有订单",
                }
            raise ValueError("该报价已转为订单，不能重复转换")
        if version.status == "rejected":
            raise ValueError("已驳回的报价不能转订单")

        # 4. 生成订单号 & 创建订单
        order_no = await generate_order_no(self.db)
        order_doc = BusinessDocument(
            doc_type="order",
            doc_no=order_no,
            customer_id=quote_doc.customer_id,
            customer_name=quote_doc.customer_name,
            project_name=quote_doc.project_name,
            sales_user_id=quote_doc.sales_user_id,
            department=quote_doc.department,
            contact_person=quote_doc.contact_person,
            contact_phone=quote_doc.contact_phone,
            status="pending_confirm",
            total_amount=float(version.total_amount or 0),
            source_quote_id=quote_id,
        )
        self.db.add(order_doc)
        await self.db.flush()

        # 5. 复制报价明细行 → BusinessDocumentItem
        for line in (version.lines or []):
            width_m = float(line.width_mm / 1000) if line.width_mm else None
            height_m = float(line.height_mm / 1000) if line.height_mm else None
            item = BusinessDocumentItem(
                document_id=order_doc.id,
                item_name=line.description,
                product_id=line.product_id,
                material_id=line.material_id,
                width=width_m,
                width_unit="m" if width_m else None,
                height=height_m,
                height_unit="m" if height_m else None,
                quantity=float(line.quantity or 1),
                unit=line.unit or "件",
                unit_price=float(line.unit_price or 0),
                subtotal_amount=float(line.amount or 0),
            )
            self.db.add(item)

        # 5b. 自动创建生产任务（每个报价明细行 → 一个生产任务）
        from app.models.task import ProductionTask
        from app.services.number_generator import generate_production_no

        prod_task_count = 0
        for line in (version.lines or []):
            if not line.description:
                continue
            prod_no = await generate_production_no(self.db)
            width_m = float(line.width_mm / 1000) if line.width_mm else None
            height_m = float(line.height_mm / 1000) if line.height_mm else None
            prod_task = ProductionTask(
                production_no=prod_no,
                document_id=order_doc.id,
                customer_id=quote_doc.customer_id,
                project_name=line.description,
                status="pending",
                material_id=line.material_id,
                width=width_m,
                height=height_m,
                length=float(line.length_m) if line.length_m else None,
                quantity=float(line.quantity or 1),
            )
            self.db.add(prod_task)
            prod_task_count += 1

        # ── 安装任务 + 车辆需求 + 财务应收 + 图稿快照 ──
        from app.models.task import InstallationTask
        from app.models.vehicle import VehicleUseRequest
        from app.models.outsource import OutsourceTask
        from app.models.payment import Payment
        from app.services.number_generator import generate_installation_no

        install_task = None
        vehicle_request = None
        payment_recv = None
        outsourced_processes = []

        has_installation = prod_task_count > 0 and (quote_doc.contact_person or quote_doc.contact_phone)
        if has_installation:
            install_no = await generate_installation_no(self.db)
            install_task = InstallationTask(
                installation_no=install_no,
                document_id=order_doc.id,
                customer_id=quote_doc.customer_id,
                project_name=quote_doc.project_name or f"安装-{order_no}",
                status="pending",
                contact_name=quote_doc.contact_person,
                contact_phone=quote_doc.contact_phone,
                address=quote_doc.installation_address,
            )
            self.db.add(install_task)
            await self.db.flush()

            # 5c-i. 车辆使用申请草稿（关联安装任务，status=draft 不自动派车）

            vreq = VehicleUseRequest(
                request_no=f"VR-{uuid.uuid4().hex[:8].upper()}-{datetime.now().strftime('%Y%m%d')}",
                requester_id=current_user_id,
                reason="installation",
                related_order_id=order_doc.id,
                related_install_task_id=install_task.id,
                destination=quote_doc.installation_address,
                status="draft",
                remark="来自报价自动转换，请确认用车需求后提交审批",
            )
            self.db.add(vreq)
            vehicle_request = vreq

        # 5d. 外协工艺检查 — 根据 Product.allows_outsource 判断
        from app.models.product import Product as ProdModel
        product_ids = [
            line.product_id for line in (version.lines or [])
            if line.product_id
        ]
        products_map = {}
        if product_ids:
            rp = await self.db.execute(
                select(ProdModel).where(ProdModel.id.in_(set(product_ids)))
            )
            for prod in rp.scalars().all():
                products_map[prod.id] = prod
        for line in (version.lines or []):
            prod = products_map.get(line.product_id) if line.product_id else None
            if prod and getattr(prod, 'allows_outsource', False):
                outsourced_processes.append({
                    "line_description": line.description,
                    "product_id": str(line.product_id),
                    "product_name": prod.name,
                })

        # 5e. 财务应收草稿（不自动确认收款）
        if float(version.total_amount or 0) > 0:
            from app.services.number_generator import generate_payment_no
            pay_no = await generate_payment_no(self.db)
            payment_recv = Payment(
                payment_no=pay_no,
                document_id=order_doc.id,
                customer_id=quote_doc.customer_id,
                amount=float(version.total_amount),
                paid_at=None,
                remark="来自报价自动转换，待收款",
                created_by=current_user_id,
                is_voided=False,
            )
            self.db.add(payment_recv)

        # 5f. 图稿指纹快照
        from app.models.cdr_quote import DrawingSnapshot
        drawing_fingerprint = None
        r_snap = await self.db.execute(
            select(DrawingSnapshot)
            .where(DrawingSnapshot.quote_id == quote_id)
            .order_by(DrawingSnapshot.created_at.desc()).limit(1)
        )
        drawing_snap = r_snap.scalar_one_or_none()
        if drawing_snap:
            drawing_fingerprint = drawing_snap.drawing_fingerprint

        # 6. 状态日志（先记录，再改状态）
        now = datetime.now()
        old_quote_status = quote_doc.status
        self.db.add(BusinessDocumentStatusLog(
            document_id=order_doc.id,
            from_status=None,
            to_status="pending_confirm",
            reason="来自CDR智能报价转换",
            operated_by=current_user_id,
            operated_at=now,
        ))
        self.db.add(BusinessDocumentStatusLog(
            document_id=quote_id,
            from_status=old_quote_status,
            to_status="converted",
            reason="已转为订单",
            operated_by=current_user_id,
            operated_at=now,
        ))

        # 7. 更新报价 header 状态为 converted
        quote_doc.status = "converted"

        # 8. 更新版本状态
        version.status = "converted"

        # 9. 审计日志
        audit_after = {
            "order_id": str(order_doc.id),
            "order_no": order_no,
            "production_task_count": prod_task_count,
            "has_installation": has_installation,
            "has_vehicle_request": vehicle_request is not None,
            "has_payment_draft": payment_recv is not None,
        }
        if outsourced_processes:
            audit_after["outsourced_processes"] = outsourced_processes
        if drawing_fingerprint:
            audit_after["drawing_fingerprint"] = drawing_fingerprint

        await self.repo.create_audit_log({
            "quote_id": quote_id,
            "quote_version_id": version.id,
            "actor_id": current_user_id,
            "action": "converted_to_order",
            "after_json": audit_after,
        })

        await self.db.commit()

        result = {
            "id": str(order_doc.id),
            "doc_no": order_no,
            "project_name": order_doc.project_name,
            "total_amount": float(order_doc.total_amount),
            "status": "pending_confirm",
            "production_tasks_created": prod_task_count,
            "has_installation_task": has_installation,
            "has_vehicle_request": vehicle_request is not None,
            "has_payment_draft": payment_recv is not None,
        }
        if outsourced_processes:
            result["outsourced_processes"] = outsourced_processes
        if drawing_fingerprint:
            result["drawing_fingerprint"] = drawing_fingerprint
        return result


    # ── 几何分析 ─────────────────────────────────────────────

    async def analyze_geometry_from_capture(self, capture_id: UUID) -> dict:
        """从 CDR capture_payload 分析几何数据返回结果。"""
        from app.services.geometry_service import geometry_service
        capture = await self.repo.get_capture_session(capture_id)
        if not capture:
            raise ValueError("采集记录不存在")
        payload = capture.capture_payload_json or {}
        result = geometry_service.analyze_cdr_payload(payload)
        return result

    async def save_quote_geometry(self, quote_id: UUID, version_id: UUID) -> list[dict]:
        """从报价版本自动创建几何分析记录。"""
        from app.services.geometry_service import geometry_service
        from sqlalchemy import select
        from app.models.cdr_quote import DrawingSnapshot
        version = await self.repo.get_version(version_id)
        if not version:
            return []

        # Get latest snapshot for hole data
        r_snap = await self.db.execute(
            select(DrawingSnapshot)
            .where(DrawingSnapshot.quote_id == quote_id)
            .order_by(DrawingSnapshot.created_at.desc()).limit(1)
        )
        snap = r_snap.scalar_one_or_none()
        captured_holes = None
        if snap and snap.geometry_summary_json:
            captured_holes = snap.geometry_summary_json.get("holes_detected")

        results = []
        for line in (version.lines or []):
            if not line.width_mm and not line.height_mm:
                continue

            geometry_data = {
                "quote_line_id": line.id,
                "quote_id": quote_id,
                "net_area_mm2": None,
                "hole_area_mm2": None,
                "curve_length_mm": line.length_m,
                "is_open_curve": False,
                "is_estimated": True,
            }

            if line.width_mm and line.height_mm:
                if captured_holes:
                    net = geometry_service.calculate_net_area(
                        line.width_mm, line.height_mm, captured_holes
                    )
                    geometry_data["net_area_mm2"] = float(net["net_area_mm2"])
                    geometry_data["hole_area_mm2"] = float(net["hole_area_mm2"])
                    geometry_data["is_estimated"] = net.get("is_estimated", True)

            geo = await self.repo.create_geometry(geometry_data)
            results.append({
                "id": str(geo.id),
                "quote_line_id": str(geo.quote_line_id) if geo.quote_line_id else None,
                "net_area_mm2": geo.net_area_mm2,
            })

        return results

    async def get_quote_geometry(self, quote_id: UUID) -> list[dict]:
        """获取报价所有行的几何分析。"""
        records = await self.repo.list_geometry_by_quote(quote_id)
        return [self._geometry_to_dict(g) for g in records]

    async def get_line_geometry(self, quote_line_id: UUID) -> dict | None:
        """获取指定报价行的几何分析。"""
        g = await self.repo.get_geometry(quote_line_id)
        if g:
            return self._geometry_to_dict(g)
        return None

    def _geometry_to_dict(self, g: Any) -> dict:
        return {
            "id": str(g.id),
            "quote_line_id": str(g.quote_line_id) if g.quote_line_id else None,
            "quote_id": str(g.quote_id) if g.quote_id else None,
            "net_area_mm2": float(g.net_area_mm2) if g.net_area_mm2 else None,
            "hole_area_mm2": float(g.hole_area_mm2) if g.hole_area_mm2 else None,
            "curve_length_mm": float(g.curve_length_mm) if g.curve_length_mm else None,
            "is_open_curve": g.is_open_curve,
            "overlap_count": g.overlap_count,
            "overlap_area_mm2": float(g.overlap_area_mm2) if g.overlap_area_mm2 else None,
            "sheet_count": g.sheet_count,
            "sheet_utilization_pct": float(g.sheet_utilization_pct) if g.sheet_utilization_pct else None,
            "is_estimated": g.is_estimated,
            "nesting_json": g.nesting_json,
            "analysis_json": g.analysis_json,
        }

        # ── 审计日志查询 ──

    async def list_audit_logs(self, quote_id: UUID) -> list[dict]:
        from sqlalchemy import select
        from app.models.cdr_quote import QuoteAuditLog
        r = await self.db.execute(
            select(QuoteAuditLog)
            .where(QuoteAuditLog.quote_id == quote_id)
            .order_by(QuoteAuditLog.created_at.desc())
        )
        logs = r.scalars().all()
        return [{
            "id": str(log.id),
            "actor_id": str(log.actor_id),
            "action": log.action,
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        } for log in logs]


    # ── 设备管理 ──

    async def register_device(self, data: dict, current_user_id: UUID) -> dict:
        """注册 CDR 插件设备。"""
        device_code = data.get("device_code", "")
        existing = await self.repo.get_device_by_code(device_code)
        if existing:
            existing.employee_id = current_user_id
            existing.device_name = data.get("device_name", existing.device_name)
            existing.plugin_version = data.get("plugin_version")
            existing.bridge_version = data.get("bridge_version")
            existing.last_seen_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return {"id": str(existing.id), "device_code": existing.device_code, "status": existing.status}

        device_data = {
            "device_code": device_code,
            "device_name": data.get("device_name", ""),
            "employee_id": current_user_id,
            "machine_fingerprint_hash": data.get("machine_fingerprint_hash", device_code),
            "plugin_version": data.get("plugin_version"),
            "bridge_version": data.get("bridge_version"),
            "last_seen_at": datetime.utcnow(),
            "status": "active",
        }
        device = await self.repo.create_device(device_data)
        return {"id": str(device.id), "device_code": device.device_code, "status": device.status}

    async def list_devices(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        """获取设备列表。"""
        devices, total = await self.repo.list_devices(page, page_size)
        result = []
        for d in devices:
            result.append({
                "id": str(d.id),
                "device_code": d.device_code,
                "device_name": d.device_name,
                "employee_id": str(d.employee_id) if d.employee_id else None,
                "plugin_version": d.plugin_version,
                "bridge_version": d.bridge_version,
                "status": d.status,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })
        return result, total

    async def revoke_device(self, device_id: UUID) -> None:
        """撤销设备。"""
        await self.repo.revoke_device(device_id)

    # ── 图稿采集 ──

    async def create_capture(self, data: dict, current_user_id: UUID) -> dict:
        """创建图稿采集会话。"""
        from datetime import datetime, timedelta

        device_code = data.get("device_code", "")
        device = await self.repo.get_device_by_code(device_code)
        if not device:
            raise ValueError(f"设备 {device_code} 未注册")
        if device.status == "revoked":
            raise ValueError(f"设备 {device_code} 已被撤销")

        # Update device last seen
        await self.repo.update_device_last_seen(device.id)

        # Generate session code
        import hashlib, random
        raw = f"{device_code}-{datetime.utcnow().isoformat()}-{random.randint(1000, 9999)}"
        session_code = "CAP-" + hashlib.md5(raw.encode()).hexdigest()[:12].upper()

        doc = data.get("document", {})
        sel = data.get("selection", {})

        capture_data = {
            "session_code": session_code,
            "device_id": device.id,
            "employee_id": current_user_id,
            "document_name": doc.get("document_name", ""),
            "page_index": doc.get("active_page_index", 0),
            "page_name": doc.get("active_page_name", ""),
            "selection_count": sel.get("selection_count", 0),
            "drawing_fingerprint": data.get("drawing_fingerprint", ""),
            "capture_payload_json": data,
            "warnings_json": data.get("warnings", []),
            "captured_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30),
        }
        capture = await self.repo.create_capture_session(capture_data)
        return {
            "id": str(capture.id),
            "session_code": capture.session_code,
            "document_name": capture.document_name,
            "selection_count": capture.selection_count,
            "drawing_fingerprint": capture.drawing_fingerprint,
            "captured_at": capture.captured_at.isoformat() if capture.captured_at else None,
        }

    async def get_capture(self, capture_id: UUID) -> dict | None:
        """获取采集详情。"""
        capture = await self.repo.get_capture_session(capture_id)
        if not capture:
            return None
        return {
            "id": str(capture.id),
            "session_code": capture.session_code,
            "device_id": str(capture.device_id) if capture.device_id else None,
            "employee_id": str(capture.employee_id) if capture.employee_id else None,
            "document_name": capture.document_name,
            "selection_count": capture.selection_count,
            "drawing_fingerprint": capture.drawing_fingerprint,
            "capture_payload": capture.capture_payload_json,
            "warnings": capture.warnings_json,
            "captured_at": capture.captured_at.isoformat() if capture.captured_at else None,
            "expires_at": capture.expires_at.isoformat() if capture.expires_at else None,
        }

    async def create_quote_from_capture(self, capture_id: UUID, data: dict, current_user_id: UUID) -> dict:
        """根据图稿采集创建报价草稿。"
        """
        from app.models.business_document import BusinessDocument

        capture = await self.repo.get_capture_session(capture_id)
        if not capture:
            raise ValueError("采集记录不存在")

        # Create a CDR quote (business_document with doc_type="quote")
        from app.services.number_generator import generate_quote_no
        quote_no = await generate_quote_no(self.db)

        doc = BusinessDocument(
            doc_type="quote",
            doc_no=quote_no,
            status="draft",
            quote_mode="cdr",
            customer_id=data.get("customer_id"),
            customer_name=data.get("customer_name", ""),
            project_name=data.get("project_name", f"CDR: {capture.document_name or ''}"),
            department=data.get("department", ""),
            subtotal_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal(str(data.get("tax_rate", 0.13))),
            tax_amount=Decimal("0"),
            total_amount=Decimal("0"),
            paid_amount=Decimal("0"),
            cost_amount=Decimal("0"),
            gross_profit=Decimal("0"),
            remark=data.get("notes", f"来源：CDR 图稿采集 {capture.session_code}"),
            created_by=current_user_id,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        # Create drawing snapshot
        snapshot_data = {
            "snapshot_code": "DS-" + capture.session_code,
            "capture_session_id": capture.id,
            "quote_id": doc.id,
            "drawing_fingerprint": capture.drawing_fingerprint or "",
            "geometry_summary_json": data.get("geometry_summary"),
            "object_summary_json": data.get("object_summary"),
            "created_by": current_user_id,
        }
        await self.repo.create_drawing_snapshot(snapshot_data)

        # Log audit
        await self.repo.create_audit_log({
            "quote_id": doc.id,
            "actor_id": current_user_id,
            "action": "quote.created_from_capture",
            "after_json": {"capture_session_id": str(capture.id), "quote_no": quote_no},
        })

        return {
            "id": str(doc.id),
            "quote_no": doc.doc_no,
            "status": doc.status,
            "project_name": doc.project_name,
            "capture_session_id": str(capture.id),
            "message": "报价草稿已创建，请完善报价明细",
        }
