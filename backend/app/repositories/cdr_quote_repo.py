"""CDR 智能报价——数据仓库层。"""

from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload

from app.models.cdr_quote import (
    PriceRuleSet, CdrPriceRule,
    CustomerPriceAgreement,
    QuoteVersion, QuoteLine, QuoteLineProcess,
    QuoteApproval, QuoteAuditLog,
    CdrDevice, CdrCaptureSession, DrawingSnapshot, QuoteGeometry,
)
from app.models.product import Product, Material, Process


class CdrQuoteRepository:
    """CDR 报价数据仓库。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 产品/材料/工艺 ──

    async def get_product(self, product_id: UUID) -> Product | None:
        r = await self.db.execute(select(Product).where(Product.id == product_id))
        return r.scalar_one_or_none()

    async def get_material(self, material_id: UUID) -> Material | None:
        r = await self.db.execute(select(Material).where(Material.id == material_id))
        return r.scalar_one_or_none()

    async def get_process(self, process_id: UUID) -> Process | None:
        r = await self.db.execute(select(Process).where(Process.id == process_id))
        return r.scalar_one_or_none()

    async def get_processes(self, ids: list[UUID]) -> list[Process]:
        r = await self.db.execute(select(Process).where(Process.id.in_(ids)))
        return list(r.scalars().all())

    # ── 报价版本 ──

    async def create_version(self, data: dict) -> QuoteVersion:
        v = QuoteVersion(**data)
        self.db.add(v)
        await self.db.flush()
        return v

    async def get_version(self, version_id: UUID) -> QuoteVersion | None:
        r = await self.db.execute(
            select(QuoteVersion)
            .options(selectinload(QuoteVersion.lines).selectinload(QuoteLine.processes))
            .where(QuoteVersion.id == version_id)
        )
        return r.scalar_one_or_none()

    async def get_latest_version(self, quote_id: UUID) -> QuoteVersion | None:
        r = await self.db.execute(
            select(QuoteVersion)
            .options(selectinload(QuoteVersion.lines).selectinload(QuoteLine.processes))
            .where(QuoteVersion.quote_id == quote_id)
            .order_by(QuoteVersion.version_no.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    async def list_versions(self, quote_id: UUID) -> list[QuoteVersion]:
        r = await self.db.execute(
            select(QuoteVersion)
            .where(QuoteVersion.quote_id == quote_id)
            .order_by(QuoteVersion.version_no.desc())
        )
        return list(r.scalars().all())

    async def get_max_version_no(self, quote_id: UUID) -> int | None:
        r = await self.db.execute(
            select(func.max(QuoteVersion.version_no)).where(QuoteVersion.quote_id == quote_id)
        )
        return r.scalar()
    # ── QuoteGeometry 几何分析 CRUD ──────────────────────────

    async def create_geometry(self, data: dict) -> QuoteGeometry:
        """创建几何分析记录。"""
        g = QuoteGeometry(**data)
        self.db.add(g)
        await self.db.flush()
        return g

    async def get_geometry(self, quote_line_id: UUID) -> QuoteGeometry | None:
        """获取指定报价行的几何分析。"""
        r = await self.db.execute(
            select(QuoteGeometry).where(QuoteGeometry.quote_line_id == quote_line_id)
        )
        return r.scalar_one_or_none()

    async def list_geometry_by_quote(self, quote_id: UUID) -> list[QuoteGeometry]:
        """获取报价所有行的几何分析。"""
        r = await self.db.execute(
            select(QuoteGeometry).where(QuoteGeometry.quote_id == quote_id)
        )
        return list(r.scalars().all())

    async def update_geometry(self, geometry_id: UUID, data: dict) -> QuoteGeometry | None:
        """更新几何分析记录。"""
        from sqlalchemy import update as sa_update
        await self.db.execute(
            sa_update(QuoteGeometry).where(QuoteGeometry.id == geometry_id).values(**data)
        )
        await self.db.flush()
        r = await self.db.execute(select(QuoteGeometry).where(QuoteGeometry.id == geometry_id))
        return r.scalar_one_or_none()

    async def delete_geometry(self, geometry_id: UUID) -> None:
        """删除几何分析记录。"""
        from sqlalchemy import delete as sa_delete
        await self.db.execute(sa_delete(QuoteGeometry).where(QuoteGeometry.id == geometry_id))
        await self.db.flush()


    async def update_version_status(self, version_id: UUID, status: str) -> bool:
        r = await self.db.execute(
            update(QuoteVersion).where(QuoteVersion.id == version_id).values(status=status)
        )
        return r.rowcount > 0

    # ── 报价行 ──

    async def create_line(self, data: dict) -> QuoteLine:
        line = QuoteLine(**data)
        self.db.add(line)
        await self.db.flush()
        return line

    async def get_line(self, line_id: UUID) -> QuoteLine | None:
        r = await self.db.execute(
            select(QuoteLine).options(selectinload(QuoteLine.processes)).where(QuoteLine.id == line_id)
        )
        return r.scalar_one_or_none()

    async def delete_line(self, line_id: UUID) -> bool:
        r = await self.db.execute(delete(QuoteLine).where(QuoteLine.id == line_id))
        return r.rowcount > 0

    async def create_line_process(self, data: dict) -> QuoteLineProcess:
        lp = QuoteLineProcess(**data)
        self.db.add(lp)
        await self.db.flush()
        return lp

    # ── 规则集 ──

    async def create_rule_set(self, data: dict) -> PriceRuleSet:
        rs = PriceRuleSet(**data)
        self.db.add(rs)
        await self.db.flush()
        return rs

    async def get_rule_set(self, rule_set_id: UUID) -> PriceRuleSet | None:
        r = await self.db.execute(
            select(PriceRuleSet).options(selectinload(PriceRuleSet.rules)).where(PriceRuleSet.id == rule_set_id)
        )
        return r.scalar_one_or_none()

    async def list_rule_sets(self) -> list[PriceRuleSet]:
        r = await self.db.execute(
            select(PriceRuleSet).order_by(PriceRuleSet.created_at.desc())
        )
        return list(r.scalars().all())

    async def get_active_rule_set(self) -> PriceRuleSet | None:
        """获取当前生效的已发布规则集。"""
        from datetime import date
        today = date.today().isoformat()
        r = await self.db.execute(
            select(PriceRuleSet)
            .options(selectinload(PriceRuleSet.rules))
            .where(PriceRuleSet.status == "published")
            .where(
                (PriceRuleSet.effective_from.is_(None)) | (PriceRuleSet.effective_from <= today)
            )
            .where(
                (PriceRuleSet.effective_to.is_(None)) | (PriceRuleSet.effective_to >= today)
            )
            .order_by(PriceRuleSet.version.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    # ── 客户协议价 ──

    async def get_customer_agreement(
        self, customer_id: UUID, product_id: UUID | None = None
    ) -> CustomerPriceAgreement | None:
        """查找匹配的客户协议价。"""
        from datetime import date
        today = date.today().isoformat()
        q = select(CustomerPriceAgreement).where(
            CustomerPriceAgreement.customer_id == customer_id,
            (CustomerPriceAgreement.effective_from <= today),
            (CustomerPriceAgreement.effective_to.is_(None)) | (CustomerPriceAgreement.effective_to >= today),
        )
        if product_id:
            q = q.where(
                (CustomerPriceAgreement.product_id == product_id) | (CustomerPriceAgreement.product_id.is_(None))
            )
        q = q.order_by(CustomerPriceAgreement.product_id.desc()).limit(1)
        r = await self.db.execute(q)
        return r.scalar_one_or_none()

    async def list_customer_agreements(self, customer_id: UUID | None = None) -> list[CustomerPriceAgreement]:
        q = select(CustomerPriceAgreement)
        if customer_id:
            q = q.where(CustomerPriceAgreement.customer_id == customer_id)
        q = q.order_by(CustomerPriceAgreement.created_at.desc())
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def create_customer_agreement(self, data: dict) -> CustomerPriceAgreement:
        ca = CustomerPriceAgreement(**data)
        self.db.add(ca)
        await self.db.flush()
        return ca

    # ── 审批 ──

    async def create_approval(self, data: dict) -> QuoteApproval:
        a = QuoteApproval(**data)
        self.db.add(a)
        await self.db.flush()
        return a

    async def update_approval(self, approval_id: UUID, data: dict) -> bool:
        r = await self.db.execute(
            update(QuoteApproval).where(QuoteApproval.id == approval_id).values(**data)
        )
        return r.rowcount > 0

    async def list_approvals(self, quote_id: UUID) -> list[QuoteApproval]:
        r = await self.db.execute(
            select(QuoteApproval)
            .where(QuoteApproval.quote_id == quote_id)
            .order_by(QuoteApproval.created_at.desc())
        )
        return list(r.scalars().all())

    # ── 审计日志 ──

    async def create_audit_log(self, data: dict) -> QuoteAuditLog:
        log = QuoteAuditLog(**data)
        self.db.add(log)
        await self.db.flush()
        return log

    # ── 设备 ──

    async def get_device_by_code(self, device_code: str) -> CdrDevice | None:
        r = await self.db.execute(
            select(CdrDevice).where(CdrDevice.device_code == device_code)
        )
        return r.scalar_one_or_none()

    async def create_device(self, data: dict) -> CdrDevice:
        d = CdrDevice(**data)
        self.db.add(d)
        await self.db.flush()
        return d

    # ── 采集会话 ──

    async def create_capture_session(self, data: dict) -> CdrCaptureSession:
        cs = CdrCaptureSession(**data)
        self.db.add(cs)
        await self.db.flush()
        return cs


    # ── 设备管理 ──

    async def list_devices(self, page: int = 1, page_size: int = 20) -> tuple[list[CdrDevice], int]:
        total_q = select(func.count(CdrDevice.id))
        total_r = await self.db.execute(total_q)
        total = total_r.scalar() or 0
        q = select(CdrDevice).order_by(CdrDevice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        return list(r.scalars().all()), total

    async def update_device_last_seen(self, device_id: UUID) -> None:
        q = update(CdrDevice).where(CdrDevice.id == device_id).values(last_seen_at=func.now())
        await self.db.execute(q)
        await self.db.commit()

    async def revoke_device(self, device_id: UUID) -> None:
        q = update(CdrDevice).where(CdrDevice.id == device_id).values(status="revoked", revoked_at=func.now())
        await self.db.execute(q)
        await self.db.commit()

    # ── 采集会话 ──

    async def get_capture_session(self, session_id: UUID) -> CdrCaptureSession | None:
        r = await self.db.execute(select(CdrCaptureSession).where(CdrCaptureSession.id == session_id))
        return r.scalar_one_or_none()

    async def get_capture_session_by_code(self, session_code: str) -> CdrCaptureSession | None:
        r = await self.db.execute(select(CdrCaptureSession).where(CdrCaptureSession.session_code == session_code))
        return r.scalar_one_or_none()

    async def update_capture_session(self, session_id: UUID, data: dict) -> bool:
        q = update(CdrCaptureSession).where(CdrCaptureSession.id == session_id).values(**data)
        await self.db.execute(q)
        await self.db.commit()
        return True

    # ── 图稿快照 ──

    async def create_drawing_snapshot(self, data: dict) -> DrawingSnapshot:
        obj = DrawingSnapshot(**data)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    # ── 报价查询 ──

    async def get_quote(self, quote_id: UUID):
        from app.models.business_document import BusinessDocument
        r = await self.db.execute(
            select(BusinessDocument).where(BusinessDocument.id == quote_id, BusinessDocument.doc_type == "quote")
        )
        return r.scalar_one_or_none()

    async def list_quotes(self, page: int = 1, page_size: int = 20, status: str | None = None, keyword: str | None = None) -> tuple[list, int]:
        from app.models.business_document import BusinessDocument
        q = select(BusinessDocument).where(BusinessDocument.doc_type == "quote")
        count_q = select(func.count(BusinessDocument.id)).where(BusinessDocument.doc_type == "quote")
        if status:
            q = q.where(BusinessDocument.status == status)
            count_q = count_q.where(BusinessDocument.status == status)
        if keyword:
            like = f"%{keyword}%"
            q = q.where((BusinessDocument.doc_no.like(like)) | (BusinessDocument.project_name.like(like)) | (BusinessDocument.customer_name.like(like)))
            count_q = count_q.where((BusinessDocument.doc_no.like(like)) | (BusinessDocument.project_name.like(like)) | (BusinessDocument.customer_name.like(like)))
        total_r = await self.db.execute(count_q)
        total = total_r.scalar() or 0
        q = q.order_by(BusinessDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(q)
        return list(r.scalars().all()), total
