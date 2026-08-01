"""CDR 智能报价——API 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission, PERM_CDR_QUOTE_READ, PERM_CDR_QUOTE_CREATE, PERM_CDR_QUOTE_APPROVE, PERM_CDR_QUOTE_CONVERT, PERM_CDR_QUOTE_DELETE
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.services.cdr_quote_service import CdrQuoteService

router = APIRouter(prefix="/cdr", tags=["CDR 智能报价"])


# ── 报价列表 / 详情 ─────────────────────────────────────────────

@router.get("/quotes")
async def list_cdr_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """CDR 智能报价列表。"""
    service = CdrQuoteService(db)
    quotes, total = await service.list_quotes(page, page_size, status, keyword)
    return success_paginated(quotes, total, page, page_size)


@router.delete("/quotes/{quote_id}")
async def delete_cdr_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_DELETE)),
):
    """删除CDR智能报价（硬删除）。"""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote", quote_mode="cdr")
    ok = await svc.delete(quote_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="报价不存在")
    return {"code": 0, "message": "已删除", "data": None}


@router.get("/quotes/{quote_id}")
async def get_cdr_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """CDR 智能报价详情。"""
    service = CdrQuoteService(db)
    quote = await service.get_quote(quote_id)
    if not quote:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="报价不存在")
    return success(quote)


# ── 创建报价 ─────────────────────────────────────────────────────

@router.post("/quotes")
async def create_cdr_quote(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """创建CDR智能报价 header（明细通过版本接口添加）。"""
    from app.services.business_document_service import BusinessDocumentService
    svc = BusinessDocumentService(db, doc_type="quote", quote_mode="cdr")
    data["doc_type"] = "quote"
    # CDR line items are managed through the version API (QuoteLine), not BusinessDocumentItem
    data.pop("items", None)
    quote = await svc.create(data)
    return success(quote)


# ── 报价试算 ────────────────────────────────────────────────────

@router.post("/pricing/calculate")
async def calculate_price(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """报价试算（不保存，返回规则执行明细）。"""
    service = CdrQuoteService(db)
    result = await service.calculate(data)
    return success(result)


# ── 报价版本 ────────────────────────────────────────────────────

@router.post("/quotes/{quote_id}/versions")
async def create_version(
    quote_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """为报价创建新版本（含明细行，自动试算）。"""
    service = CdrQuoteService(db)
    version = await service.create_quote_version(quote_id, data, current_user.id)
    return success(version)


@router.get("/quotes/{quote_id}/versions/latest")
async def get_latest_version(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价最新版本。"""
    service = CdrQuoteService(db)
    version = await service.get_latest_version(quote_id)
    return success(version)


@router.get("/quotes/{quote_id}/versions")
async def list_versions(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价版本历史。"""
    service = CdrQuoteService(db)
    versions = await service.list_versions(quote_id)
    return success(versions)


# ── 审批 ────────────────────────────────────────────────────────

@router.get("/quotes/{quote_id}/approvals")
async def list_cdr_approvals(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价审批记录列表。"""
    service = CdrQuoteService(db)
    approvals = await service.list_approvals(quote_id)
    return success(approvals)


@router.post("/quotes/{quote_id}/approvals")
async def request_approval(
    quote_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """请求报价审批。"""
    service = CdrQuoteService(db)
    result = await service.request_approval(quote_id, data, current_user.id)
    return success(result)


@router.post("/approvals/{approval_id}/approve")
async def approve_quote(
    approval_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_APPROVE)),
):
    """批准报价。"""
    service = CdrQuoteService(db)
    result = await service.approve(approval_id, current_user.id, data.get("comment") if data else None)
    return success(result)


@router.post("/approvals/{approval_id}/reject")
async def reject_quote(
    approval_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_APPROVE)),
):
    """驳回报价。"""
    service = CdrQuoteService(db)
    result = await service.reject(approval_id, current_user.id, data.get("comment") if data else None)
    return success(result)


# ── 审计日志 ────────────────────────────────────────────────────

@router.get("/quotes/{quote_id}/audit-logs")
async def list_audit_logs(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取报价审计日志。"""
    service = CdrQuoteService(db)
    logs = await service.list_audit_logs(quote_id)
    return success(logs)


# ── 转订单 ────────────────────────────────────────────────────

@router.post("/quotes/{quote_id}/convert-to-order")
async def convert_to_order(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CONVERT)),
):
    """将CDR智能报价转为销售订单（创建新订单，保留报价历史）。"""
    service = CdrQuoteService(db)
    result = await service.convert_to_order(quote_id, current_user.id)
    return success(result)


# ── 几何分析 ─────────────────────────────────────────────────

@router.post("/geometry/analyze")
async def analyze_geometry(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析几何数据（孔洞/面积/重叠），不保存。"""
    from app.services.geometry_service import geometry_service
    w = data.get("width_mm")
    h = data.get("height_mm")
    holes = data.get("holes", [])
    if w and h:
        from decimal import Decimal
        result = geometry_service.calculate_net_area(
            Decimal(str(w)), Decimal(str(h)), holes
        )
        return success({
            "bbox_area_mm2": str(result["bbox_area_mm2"]) if result["bbox_area_mm2"] is not None else None,
            "hole_area_mm2": str(result["hole_area_mm2"]) if result["hole_area_mm2"] is not None else None,
            "net_area_mm2": str(result["net_area_mm2"]) if result["net_area_mm2"] is not None else None,
            "hole_ratio": str(result["hole_ratio"]),
            "is_estimated": result["is_estimated"],
        })
    return success({"is_estimated": True, "error": "缺少 width_mm/height_mm"})


@router.post("/geometry/calculate-nesting")
async def calculate_nesting(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """板材排版试算。"""
    from app.services.nesting_service import NestingService, SimpleGridNesting
    from decimal import Decimal
    rects = data.get("rects", [])
    sheet_w = Decimal(str(data.get("sheet_width_mm", 2440)))
    sheet_h = Decimal(str(data.get("sheet_height_mm", 1220)))
    service = NestingService(SimpleGridNesting())
    result = service.calculate(rects, sheet_w, sheet_h)
    return success(result)


@router.get("/quotes/{quote_id}/geometry")
async def list_quote_geometry(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取报价所有行的几何分析。"""
    service = CdrQuoteService(db)
    result = await service.get_quote_geometry(quote_id)
    return success(result)


@router.get("/quotes/{quote_id}/lines/{line_id}/geometry")
async def get_line_geometry(
    quote_id: UUID,
    line_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """获取指定报价行的几何分析。"""
    service = CdrQuoteService(db)
    result = await service.get_line_geometry(line_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="几何分析不存在")
    return success(result)


@router.post("/quotes/{quote_id}/geometry/refresh")
async def refresh_quote_geometry(
    quote_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """刷新报价几何分析。"""
    from app.repositories.cdr_quote_repo import CdrQuoteRepository
    version_id = data.get("version_id") if data else None
    service = CdrQuoteService(db)
    if not version_id:
        version = await service.get_latest_version(quote_id)
        if not version:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="报价没有版本")
        version_id = version["id"]
    from uuid import UUID
    result = await service.save_quote_geometry(quote_id, UUID(version_id))
    return success(result)


# ── Phase 8: AI报价助手 ─────────────────────────────────────────


@router.post("/quotes/{quote_id}/process-gaps")
async def detect_process_gaps(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """检测报价工艺漏项。"""
    from app.ai.rule_based.process_gap_detector import ProcessGapDetector
    detector = ProcessGapDetector(db)
    gaps = await detector.detect_gaps_for_quote(quote_id)
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for g in gaps:
        severity_counts[g["severity"]] = severity_counts.get(g["severity"], 0) + 1
    return success({
        "mode": "rule_based",
        "gaps": gaps,
        "gap_count": len(gaps),
        "summary": severity_counts,
    })


@router.post("/quotes/{quote_id}/generate-description")
async def generate_quote_description(
    quote_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """生成报价说明草稿。"""
    from app.ai.rule_based.quote_description_generator import QuoteDescriptionGenerator
    opts = data or {}
    gen = QuoteDescriptionGenerator(db)
    result = await gen.generate(
        quote_id,
        customer_id=opts.get("customer_id"),
        options=opts,
    )
    return success(result)


@router.post("/quotes/{quote_id}/price-anomaly")
async def check_price_anomaly(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """检测报价价格异常。"""
    from app.ai.rule_based.cdr_anomaly_detector import CdrPriceAnomalyDetector
    detector = CdrPriceAnomalyDetector(db)
    anomalies = await detector.check_quote(quote_id)
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for a in anomalies:
        severity_counts[a["severity"]] = severity_counts.get(a["severity"], 0) + 1
    return success({
        "mode": "rule_based",
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
        "summary": severity_counts,
    })


@router.post("/pricing/anomaly-check")
async def check_calculation_anomaly(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """试算价格异常检查（不保存）。"""
    from app.ai.rule_based.cdr_anomaly_detector import CdrPriceAnomalyDetector
    detector = CdrPriceAnomalyDetector(db)
    anomalies = await detector.check_calculation(data)
    return success({
        "mode": "rule_based",
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    })


@router.get("/quotes/{quote_id}/deviation-analysis")
async def analyze_deviation(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """预计与实际偏差分析。"""
    from app.ai.rule_based.deviation_analyzer import DeviationAnalyzer
    analyzer = DeviationAnalyzer(db)
    result = await analyzer.analyze_quote(quote_id)
    return success(result)


@router.get("/orders/{order_id}/deviation-analysis")
async def analyze_order_deviation(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """订单级预计与实际偏差分析。"""
    from app.ai.rule_based.deviation_analyzer import DeviationAnalyzer
    analyzer = DeviationAnalyzer(db)
    result = await analyzer.analyze_order(order_id)
    return success(result)


@router.post("/quotes/{quote_id}/ai-assist")
async def ai_assist_quote(
    quote_id: UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """AI综合报价助手——同时返回工艺漏项、价格异常、偏差分析。"""
    opts = data or {}
    result = {
        "process_gaps": [],
        "price_anomalies": [],
        "deviation_analysis": None,
        "quote_description": None,
    }

    # 工艺漏项
    from app.ai.rule_based.process_gap_detector import ProcessGapDetector
    pg = ProcessGapDetector(db)
    result["process_gaps"] = await pg.detect_gaps_for_quote(quote_id)

    # 价格异常
    from app.ai.rule_based.cdr_anomaly_detector import CdrPriceAnomalyDetector
    pa = CdrPriceAnomalyDetector(db)
    result["price_anomalies"] = await pa.check_quote(quote_id)

    # 偏差分析
    from app.ai.rule_based.deviation_analyzer import DeviationAnalyzer
    da = DeviationAnalyzer(db)
    try:
        result["deviation_analysis"] = await da.analyze_quote(quote_id)
    except Exception:
        result["deviation_analysis"] = {"error": "偏差分析异常"}

    return success(result)

# ── 设备管理 ─────────────────────────────────────────────────

@router.post("/devices")
async def register_device(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """注册 CDR 插件设备。"""
    service = CdrQuoteService(db)
    device = await service.register_device(data, current_user.id)
    return success(device)


@router.get("/devices")
async def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """设备列表。"""
    service = CdrQuoteService(db)
    devices, total = await service.list_devices(page, page_size)
    return success_paginated(devices, total, page, page_size)


@router.post("/devices/{device_id}/revoke")
async def revoke_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """撤销设备授权。"""
    service = CdrQuoteService(db)
    await service.revoke_device(device_id)
    return success({"message": "设备已撤销"})


# ── 图稿采集 ─────────────────────────────────────────────────

@router.post("/captures")
async def create_capture(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """CDR 插件提交图稿采集数据。"""
    service = CdrQuoteService(db)
    capture = await service.create_capture(data, current_user.id)
    return success(capture)


@router.get("/captures/{capture_id}")
async def get_capture(
    capture_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取图稿采集详情。"""
    service = CdrQuoteService(db)
    capture = await service.get_capture(capture_id)
    if not capture:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="采集记录不存在")
    return success(capture)


@router.post("/captures/{capture_id}/create-quote-draft")
async def create_quote_from_capture(
    capture_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """根据图稿采集创建报价草稿。"""
    service = CdrQuoteService(db)
    quote = await service.create_quote_from_capture(capture_id, data, current_user.id)
    return success(quote)


# ── 设计文件上传 ─────────────────────────────────────────────────

import uuid as _uuid
from fastapi import UploadFile, File as FastAPIFile
from app.services.cdr_design_service import CdrDesignService


@router.post("/quotes/{quote_id}/upload")
async def upload_design_file(
    quote_id: str,
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """上传设计文件（.cdr / .svg / .pdf / .ai 等），关联到报价。"""
    service = CdrDesignService(db)
    try:
        result = await service.upload_design_file(quote_id, file, current_user.id)
        return success(result)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.get("/quotes/{quote_id}/attachments")
async def list_attachments(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出报价关联的设计文件。"""
    service = CdrDesignService(db)
    return success(await service.list_attachments(quote_id))


@router.delete("/attachments/{att_id}")
async def delete_attachment(
    att_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_CREATE)),
):
    """删除设计附件。"""
    service = CdrDesignService(db)
    try:
        await service.delete_attachment(att_id)
        return success({"message": "已删除"})
    except ValueError as e:
        return {"code": 40401, "message": str(e), "data": None}


@router.post("/attachments/{att_id}/parse-svg")
async def parse_svg(
    att_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_CDR_QUOTE_READ)),
):
    """解析已上传的 SVG 附件，提取图形尺寸。"""
    service = CdrDesignService(db)
    try:
        result = await service.parse_svg(att_id)
        return success(result)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}


@router.post("/quotes/{quote_id}/ai-assist-description")
async def ai_assist_from_description(
    quote_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 根据文字描述 + 已上传文件，生成报价明细建议。"""
    service = CdrDesignService(db)
    try:
        result = await service.ai_assist_from_description(
            quote_id, data.get("description", ""), current_user.id
        )
        return success(result)
    except ValueError as e:
        return {"code": 40001, "message": str(e), "data": None}
