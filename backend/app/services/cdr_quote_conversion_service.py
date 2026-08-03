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


class CdrQuoteConversionService(CdrQuoteServiceBase):
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
        from app.services.cdr_quote_line_adapter import to_business_document_item_data

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
        from app.services.order_customer_service import ensure_document_customer

        await ensure_document_customer(
            self.db,
            quote_doc,
            current_user_id,
        )

        # 4. 生成订单号 & 创建订单
        order_no = await generate_order_no(self.db)
        total_amount = Decimal(str(version.total_amount or 0))
        order_doc = BusinessDocument(
            doc_type="order",
            doc_no=order_no,
            customer_id=quote_doc.customer_id,
            customer_name=quote_doc.customer_name,
            project_name=quote_doc.project_name,
            sales_user_id=quote_doc.sales_user_id,
            department=quote_doc.department,
            # 联系人不再从报价单继承：订单/报价/验收各看各的联系人，订单联系人由订单编辑填写
            contact_person=None,
            contact_phone=None,
            status="pending_confirm",
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            unpaid_amount=total_amount,
            cost_amount=Decimal("0"),
            gross_profit=total_amount,
            source_quote_id=quote_id,
        )
        self.db.add(order_doc)
        await self.db.flush()

        # 5. 复制报价明细行 → BusinessDocumentItem
        for line in (version.lines or []):
            item = BusinessDocumentItem(
                document_id=order_doc.id,
                **to_business_document_item_data(line),
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
        from app.services.number_generator import generate_installation_no

        install_task = None
        vehicle_request = None
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
            "has_payment_draft": False,
            "receivable_amount": float(total_amount),
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
            "has_payment_draft": False,
            "receivable_amount": float(total_amount),
        }
        if outsourced_processes:
            result["outsourced_processes"] = outsourced_processes
        if drawing_fingerprint:
            result["drawing_fingerprint"] = drawing_fingerprint
        return result
