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


class CdrQuoteIntegrationService(CdrQuoteServiceBase):
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
