import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.permissions import (
    PERM_DESIGN_TASK_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_ORDER_CHANGE_STATUS,
    PERM_ORDER_CREATE,
    PERM_PAYMENT_READ,
    PERM_PAYMENT_CREATE,
    PERM_QUOTE_READ,
    PERM_CDR_QUOTE_READ,
    PERM_ORDER_VIEW_PRICE,
    PERM_ORDER_CHANGE_DATE,
    PERM_ORDER_DELETE,
    PERM_ORDER_READ,
    PERM_ORDER_TASK_ASSIGN,
    PERM_ORDER_UPDATE,
    PERM_INSTALLATION_TASK_READ,
    PERM_INSTALLATION_TASK_UPDATE,
    PERM_PRODUCTION_TASK_READ,
    PERM_PRODUCTION_TASK_UPDATE,
    PERM_SYSTEM_SUPER_ADMIN,
    PERM_TASK_COMPLETION_READ,
    require_any_permission,
    require_all_permissions,
    require_permission,
)
from app.models.user import User
from app.schemas.order import (
    OrderItemCreate,
    OrderItemDelete,
    OrderEditRequest,
    OrderItemMutationPreview,
    OrderDateMutationBase,
    OrderItemUpdate,
    OrderStatusChange,
    OrderTaskAssigneesUpdate,
    OrderCreate,
    OrderDeleteRequest,
    OrderFundMutation,
    OrderActionResolve,
)
from app.schemas.common import success, success_paginated, error
from app.services.business_document_service import (
    BusinessDocumentService,
    OrderDataMutationLocked,
    OrderItemMutationConflict,
)
from app.services.operation_log_service import log_operation, OBJ_ORDER, ACTION_STATUS_CHANGE, ACTION_DELETE
from app.services.order_task_assignment_service import (
    get_order_task_assignees,
    list_task_assignee_options,
    replace_order_task_assignees,
)
from app.services.order_task_attachment_service import (
    OrderTaskAttachmentPermissionError,
    OrderTaskAttachmentService,
)
from app.core.file_security import confined_path

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/")
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(require_permission(PERM_ORDER_CREATE))):
    from app.services.order_management_service import OrderManagementService
    try:
        return success(await OrderManagementService(db, current_user).create(data.model_dump()))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.get("/from-history/{quote_id}")
async def find_order_from_history(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    """Resolve old quotation links without creating or changing documents."""
    from sqlalchemy import select
    from app.models.business_document import BusinessDocument

    order_id = await db.scalar(
        select(BusinessDocument.id)
        .where(
            BusinessDocument.doc_type == "order",
            BusinessDocument.source_quote_id == quote_id,
            BusinessDocument.deleted_at.is_(None),
        )
        .order_by(BusinessDocument.created_at, BusinessDocument.id)
        .limit(1)
    )
    return success({"order_id": str(order_id) if order_id else None})


@router.post("/from-history/{quote_id}")
async def continue_quote_history(quote_id: UUID, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_CREATE))):
    from app.services.order_management_service import OrderManagementService
    from app.core.permissions import user_has_permission
    from app.models.business_document import BusinessDocument
    from app.schemas.order import OrderCreate
    try:
        management = OrderManagementService(db, current_user)
        await management._lock_request(quote_id)
        source = await db.get(BusinessDocument, quote_id, with_for_update=True)
        if not source or source.doc_type != "quote" or source.deleted_at or source.status == "cancelled":
            raise ValueError("历史来源不存在或已取消")
        permission = PERM_CDR_QUOTE_READ if source.quote_mode == "cdr" else PERM_QUOTE_READ
        if not user_has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="没有读取该历史来源的权限")
        from sqlalchemy import select
        existing = (await db.execute(select(BusinessDocument).where(BusinessDocument.doc_type == "order", BusinessDocument.source_quote_id == quote_id))).scalars().first()
        if existing:
            if not user_has_permission(current_user, PERM_ORDER_READ):
                raise HTTPException(status_code=403, detail="没有读取已有来源订单的权限")
            if existing.deleted_at:
                raise ValueError("该来源的订单已在回收站，请先恢复")
            return success(await management.documents.get_by_id(existing.id))
        # Legacy associations require an explicit mapping; never duplicate or
        # move financial facts merely because a historical quote is copied.
        history = BusinessDocumentService(db, doc_type="quote", quote_mode=source.quote_mode)
        relations = await history._collect_order_item_relations(source)
        if any(relations.get(key) for key in ("payments", "project_costs", "outsource_tasks", "contract_links", "framework_contract_links", "acceptance_forms")):
            raise ValueError("该历史来源已有合同、成本或执行关联，请先核对关联归属后处理，未创建重复订单")
        if source.quote_mode == "cdr":
            from app.repositories.cdr_quote_repo import CdrQuoteRepository
            from app.services.cdr_quote_line_adapter import to_business_document_item_data
            version = await CdrQuoteRepository(db).get_latest_version(quote_id)
            lines = [to_business_document_item_data(line) for line in version.lines] if version else []
        else:
            lines = [management.documents._to_order_item_input(line) for line in await history.repo.get_items(quote_id)]
        from app.services.business_document_service import _business_today
        data = OrderCreate(request_id=quote_id, order_date=_business_today(),
            header={"customer_id": str(source.customer_id) if source.customer_id else None, "customer_name": source.customer_name,
                    "project_name": source.project_name, "department": source.department, "remark": source.remark,
                    "discount_amount": source.discount_amount, "tax_rate": source.tax_rate}, items=lines,
            groups=[{"group_id": group.group_id, "group_name": group.group_name, "sort_order": group.sort_order} for group in source.groups])
        result = await management.create(data.model_dump())
        order = await db.get(BusinessDocument, UUID(result["id"]))
        order.source_quote_id = quote_id
        if source.quote_mode == "regular":
            originals = await history.repo.get_items(quote_id)
            created_items = await management.documents.repo.get_items(order.id)
            for new, original in zip(created_items, originals, strict=True):
                new.source_quote_item_id = original.id
        await db.flush()
        await management.documents.repo.create_version(order.id, await management.documents.repo.get_next_version_no(order.id),
            {"change_type": "order_from_history", "source_quote_id": str(quote_id), "source_no": source.doc_no,
             "after": await management.documents.get_by_id(order.id)}, current_user.id)
        return success(await management.documents.get_by_id(order.id))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


class CostEntry(BaseModel):
    cost_amount: float


class ContactEntry(BaseModel):
    contact_person: str | None = None
    contact_phone: str | None = None


@router.get("/")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    customer_id: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    cid = UUID(customer_id) if customer_id else None
    orders, total = await service.list_all(page, page_size, status, cid, keyword=keyword)
    return success_paginated(orders, total, page, page_size)


@router.get("/recycle/list", dependencies=[Depends(require_permission(PERM_ORDER_READ))])
async def list_deleted_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(PERM_ORDER_DELETE, PERM_PAYMENT_READ)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    orders, total = await service.list_deleted(page, page_size, keyword=keyword)
    return success_paginated(orders, total, page, page_size)


@router.get("/import-template")
async def order_import_template(current_user: User = Depends(require_any_permission(PERM_ORDER_CREATE, PERM_ORDER_UPDATE))):
    from io import BytesIO
    from urllib.parse import quote
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "订单明细"
    sheet.append(["明细分组", "项目内容", "产品/材质/工艺", "宽", "宽单位", "高", "高单位", "件数", "面积开关", "数量", "单位", "单价", "其他费用", "备注"])
    sheet.append(["门头", "灯箱", "铝型材", 1, "m", 1, "m", 1, "否", 2, "个", 100, 0, ""])
    data = BytesIO()
    workbook.save(data)
    data.seek(0)
    return StreamingResponse(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('订单明细模板.xlsx')}"})


@router.post("/import-preview")
async def order_import_preview(file: UploadFile = File(...),
    current_user: User = Depends(require_any_permission(PERM_ORDER_CREATE, PERM_ORDER_UPDATE))):
    from app.api.quotes import QUOTE_ITEM_TEMPLATE_MAP, QUOTE_ITEM_REQUIRED
    from app.utils.excel_import import parse_excel, format_value, parse_number
    from app.services.quote_calculation import normalize_quote_item_data
    if not (file.filename or "").lower().endswith(".xlsx"):
        return error(40001, "请上传 .xlsx 格式的订单明细")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        return error(40001, "导入文件不能超过 5MB")
    try:
        import zipfile
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(content)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 30 * 1024 * 1024:
                return error(40001, "Excel 解压内容过大")
        mapping = {**QUOTE_ITEM_TEMPLATE_MAP, "其他费用": "other_fee"}
        rows, errors = parse_excel(content, QUOTE_ITEM_REQUIRED, mapping)
        if errors:
            return error(40002, "；".join(str(row) for row in errors))
        if not rows or len(rows) > 1000:
            return error(40001, "请导入 1 至 1000 条明细")
        items = []
        for index, row in enumerate(rows):
            raw = {key: format_value(row.get(key)) for key in ("item_name", "group_name", "material_process", "unit", "remark")}
            for key in ("quantity", "unit_price", "width", "height", "pieces", "other_fee"):
                value = parse_number(row.get(key))
                raw[key] = value if value is not None else (1 if key in {"quantity", "pieces"} else 0)
            raw.update({"width_unit": format_value(row.get("width_unit")) or "m", "height_unit": format_value(row.get("height_unit")) or "m",
                "use_area": str(row.get("use_area") or "").strip().lower() in {"是", "1", "y", "yes", "true"}, "sort_order": index})
            if not raw["item_name"]:
                raise ValueError(f"第 {index + 2} 行项目内容不能为空")
            items.append(BusinessDocumentService._json_safe(normalize_quote_item_data(raw)))
        return success({"items": items})
    except (ValueError, zipfile.BadZipFile) as exc:
        return error(40001, str(exc))


@router.get("/task-assignee-options")
async def list_order_task_assignee_options(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_TASK_ASSIGN)),
):
    """Return employees that can be used in an order task visibility scope."""
    return success(await list_task_assignee_options(db))


@router.get("/{order_id}/task-assignees")
async def get_order_task_assignee_scope(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_TASK_ASSIGN)),
):
    try:
        return success(await get_order_task_assignees(db, UUID(order_id)))
    except ValueError as exc:
        return error(40401, str(exc))


@router.put("/{order_id}/task-assignees")
async def update_order_task_assignee_scope(
    order_id: str,
    data: OrderTaskAssigneesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_TASK_ASSIGN)),
):
    try:
        result = await replace_order_task_assignees(
            db,
            UUID(order_id),
            data.employee_ids,
            current_user.id,
        )
        return success(result)
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    order = await service.get_by_id(UUID(order_id))
    if not order:
        return {"code": 40401, "message": "订单不存在", "data": None}
    return success(order)


def _parse_order_attachment_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail=f"{label}编号无效")


_ORDER_ATTACHMENT_READ_PERMISSIONS = (
    PERM_ORDER_READ,
    PERM_DESIGN_TASK_READ,
    PERM_PRODUCTION_TASK_READ,
    PERM_INSTALLATION_TASK_READ,
    PERM_TASK_COMPLETION_READ,
)
_ORDER_ATTACHMENT_WRITE_PERMISSIONS = (
    PERM_ORDER_READ,
    PERM_DESIGN_TASK_UPDATE,
    PERM_PRODUCTION_TASK_UPDATE,
    PERM_INSTALLATION_TASK_UPDATE,
)


def _parse_optional_order_attachment_uuid(value: str | None, label: str) -> UUID | None:
    return _parse_order_attachment_uuid(value, label) if value else None


@router.get(
    "/{order_id}/attachments",
)
async def list_order_attachments(
    order_id: str,
    stage: str | None = Query(None),
    task_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_ORDER_ATTACHMENT_READ_PERMISSIONS)),
):
    """List canonical order-owned materials, optionally from a task entry."""
    service = OrderTaskAttachmentService(db)
    try:
        return success(
            await service.list_for_order(
                _parse_order_attachment_uuid(order_id, "订单"),
                stage=stage,
                task_id=_parse_optional_order_attachment_uuid(task_id, "任务"),
                viewer=current_user,
            )
        )
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        return error(40401, str(exc))


@router.post(
    "/{order_id}/attachments",
)
async def upload_order_attachment(
    order_id: str,
    stage: str = Form(...),
    task_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_ORDER_ATTACHMENT_WRITE_PERMISSIONS)),
):
    """Upload to the order/stage source; task id is optional context only."""
    service = OrderTaskAttachmentService(db)
    try:
        attachment = await service.upload(
            _parse_order_attachment_uuid(order_id, "订单"),
            stage,
            _parse_optional_order_attachment_uuid(task_id, "任务"),
            file,
            current_user.id,
            current_user.real_name or current_user.username,
            viewer=current_user,
        )
        return success(attachment)
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.get(
    "/{order_id}/attachments/{attachment_id}/file",
)
async def read_order_attachment_file(
    order_id: str,
    attachment_id: str,
    stage: str | None = Query(None),
    task_id: str | None = Query(None),
    download: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_ORDER_ATTACHMENT_READ_PERMISSIONS)),
):
    """Read an order attachment only through the authenticated API."""
    service = OrderTaskAttachmentService(db)
    try:
        attachment, stored_path = await service.get_file(
            _parse_order_attachment_uuid(order_id, "订单"),
            _parse_order_attachment_uuid(attachment_id, "附件"),
            stage=stage,
            task_id=_parse_optional_order_attachment_uuid(task_id, "任务"),
            viewer=current_user,
        )
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    media_type = (attachment.file_type or "application/octet-stream").split(";", 1)[0]
    return FileResponse(
        stored_path,
        media_type=media_type,
        filename=attachment.filename,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'"},
    )


@router.delete(
    "/{order_id}/attachments/{attachment_id}",
)
async def delete_order_attachment(
    order_id: str,
    attachment_id: str,
    stage: str | None = Query(None),
    task_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_permission(*_ORDER_ATTACHMENT_WRITE_PERMISSIONS)),
):
    """Delete an order attachment after exact order/stage authorization."""
    service = OrderTaskAttachmentService(db)
    try:
        _, relative_path = await service.delete(
            _parse_order_attachment_uuid(order_id, "订单"),
            _parse_order_attachment_uuid(attachment_id, "附件"),
            current_user.id,
            current_user.real_name or current_user.username,
            stage=stage,
            task_id=_parse_optional_order_attachment_uuid(task_id, "任务"),
            viewer=current_user,
        )
        try:
            stored_path = confined_path(settings.LOCAL_UPLOAD_DIR, relative_path)
            if os.path.isfile(stored_path):
                os.remove(stored_path)
        except HTTPException:
            # The database deletion and audit log remain authoritative; never
            # expose a malformed server path to the caller.
            pass
        return success(None)
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        return error(40401, str(exc))


@router.get("/{order_id}/task-attachments")
async def list_order_task_attachments(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    """List the three stage material groups visible from an order detail."""
    service = OrderTaskAttachmentService(db)
    try:
        return success(
            await service.list_for_order(
                _parse_order_attachment_uuid(order_id, "订单"),
                viewer=current_user,
            )
        )
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        return error(40401, str(exc))


@router.post("/{order_id}/task-attachments")
async def upload_order_task_attachment(
    order_id: str,
    task_type: str = Form(...),
    task_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    """Upload material from an order detail using only order-read permission."""
    service = OrderTaskAttachmentService(db)
    try:
        attachment = await service.upload(
            _parse_order_attachment_uuid(order_id, "订单"),
            task_type,
            _parse_optional_order_attachment_uuid(task_id, "任务"),
            file,
            current_user.id,
            current_user.real_name or current_user.username,
            viewer=current_user,
        )
        return success(attachment)
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.get("/{order_id}/task-attachments/{attachment_id}/file")
async def read_order_task_attachment_file(
    order_id: str,
    attachment_id: str,
    download: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    """Read an order attachment only after rechecking its order ownership."""
    service = OrderTaskAttachmentService(db)
    try:
        attachment, stored_path = await service.get_file(
            _parse_order_attachment_uuid(order_id, "订单"),
            _parse_order_attachment_uuid(attachment_id, "附件"),
            viewer=current_user,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    media_type = (attachment.file_type or "application/octet-stream").split(";", 1)[0]
    return FileResponse(
        stored_path,
        media_type=media_type,
        filename=attachment.filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.delete("/{order_id}/task-attachments/{attachment_id}")
async def delete_order_task_attachment(
    order_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    """Delete an order attachment after checking the exact order boundary."""
    service = OrderTaskAttachmentService(db)
    try:
        attachment, relative_path = await service.delete(
            _parse_order_attachment_uuid(order_id, "订单"),
            _parse_order_attachment_uuid(attachment_id, "附件"),
            current_user.id,
            current_user.real_name or current_user.username,
            viewer=current_user,
        )
        try:
            stored_path = confined_path(settings.LOCAL_UPLOAD_DIR, relative_path)
            if os.path.isfile(stored_path):
                os.remove(stored_path)
        except HTTPException:
            # The database deletion and audit log remain authoritative; never
            # expose a server path when a legacy file path is malformed.
            pass
        return success(None)
    except OrderTaskAttachmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        return error(40401, str(exc))


@router.get("/{order_id}/items/editability")
async def get_order_item_editability(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(await service.get_order_item_editability(UUID(order_id)))
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/order-date/preview")
async def preview_order_date_change(
    order_id: str,
    data: OrderDateMutationBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_CHANGE_DATE)),
):
    """预检订单业务下单日期变更，不修改系统创建时间或任何关联事实。"""
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.preview_order_date_change(
                UUID(order_id),
                data.order_date,
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
            )
        )
    except OrderItemMutationConflict as exc:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(exc)))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.patch("/{order_id}/order-date")
async def apply_order_date_change(
    order_id: str,
    data: OrderDateMutationBase,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_CHANGE_DATE)),
):
    """确认修改订单业务下单日期；系统 created_at 始终只读。"""
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.apply_order_date_change(
                UUID(order_id),
                data.order_date,
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
                operated_by_name=current_user.real_name or current_user.username,
                ip_address=request.client.host if request.client else None,
                preview_id=data.preview_id,
                plan_hash=data.plan_hash,
                preview_expires_at=data.preview_expires_at,
                confirm_high_risk=data.confirm_high_risk,
            )
        )
    except OrderItemMutationConflict as exc:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(exc)))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))

@router.post("/{order_id}/items/preview")
async def preview_order_item_mutation(
    order_id: str,
    data: OrderItemMutationPreview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        item_id = UUID(data.item_id) if data.item_id else None
        result = await service.preview_order_item_mutation(
            UUID(order_id),
            data.operation,
            item_id=item_id,
            data=data.item,
            expected_updated_at=data.expected_updated_at,
            reason=data.reason,
            operated_by=current_user.id,
        )
        return success(result)
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.post("/{order_id}/items/batch-preview")
async def preview_order_edit(
    order_id: str,
    data: OrderEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    """预检报价式订单编辑器提交的整批头部/明细变更。"""
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.preview_order_edit(
                UUID(order_id),
                header=data.header.model_dump(exclude_unset=True),
                # 批量编辑是完整明细快照；显式 null 表示用户要清空字段，不能丢弃。
                items=[item.model_dump(exclude_unset=True) for item in data.items],
                groups=[group.model_dump() for group in data.groups],
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
            )
        )
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.post("/{order_id}/items/batch")
async def apply_order_edit(
    order_id: str,
    data: OrderEditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    """原子应用订单编辑器的整批变更，并返回变更批次结果。"""
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.apply_order_edit(
                UUID(order_id),
                header=data.header.model_dump(exclude_unset=True),
                # 与预检保持一致，保留显式 null，确保预检与正式保存的字段语义一致。
                items=[item.model_dump(exclude_unset=True) for item in data.items],
                groups=[group.model_dump() for group in data.groups],
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
                operated_by_name=current_user.real_name or current_user.username,
                ip_address=request.client.host if request.client else None,
                preview_id=data.preview_id,
                plan_hash=data.plan_hash,
                preview_expires_at=data.preview_expires_at,
                confirm_high_risk=data.confirm_high_risk,
            )
        )
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.get("/{order_id}/items/change-batches")
async def list_order_item_change_batches(
    order_id: str,
    limit: int = Query(50, ge=1, le=200),
    change_batch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.list_order_item_change_batches(
                UUID(order_id),
                limit=limit,
                change_batch_id=change_batch_id,
            )
        )
    except ValueError as e:
        return error(40401, str(e))


@router.get("/{order_id}/items/change-batches/{change_batch_id}")
async def get_order_item_change_batch(
    order_id: str,
    change_batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.get_order_item_change_batch(
                UUID(order_id),
                change_batch_id,
            )
        )
    except ValueError as e:
        return error(40401, str(e))


@router.get("/{order_id}/items/reconciliation")
async def reconcile_order_item_change(
    order_id: str,
    change_batch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_READ)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.reconcile_order_item_change(
                UUID(order_id),
                change_batch_id=change_batch_id,
            )
        )
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/items")
async def add_order_item(
    order_id: str,
    data: OrderItemCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.mutate_order_item(
                UUID(order_id),
                "add",
                data=data.model_dump(exclude={
                    "reason", "expected_updated_at", "preview_id", "plan_hash",
                    "preview_expires_at", "confirm_high_risk",
                }),
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
                operated_by_name=current_user.real_name or current_user.username,
                ip_address=request.client.host if request.client else None,
                preview_id=data.preview_id,
                plan_hash=data.plan_hash,
                preview_expires_at=data.preview_expires_at,
                confirm_high_risk=data.confirm_high_risk,
            )
        )
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.patch("/{order_id}/items/{item_id}")
async def update_order_item(
    order_id: str,
    item_id: str,
    data: OrderItemUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.mutate_order_item(
                UUID(order_id),
                "update",
                item_id=UUID(item_id),
                data=data.model_dump(
                    exclude={
                        "reason", "expected_updated_at", "preview_id", "plan_hash",
                        "preview_expires_at", "confirm_high_risk",
                    },
                    exclude_unset=True,
                ),
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
                operated_by_name=current_user.real_name or current_user.username,
                ip_address=request.client.host if request.client else None,
                preview_id=data.preview_id,
                plan_hash=data.plan_hash,
                preview_expires_at=data.preview_expires_at,
                confirm_high_risk=data.confirm_high_risk,
            )
        )
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.delete("/{order_id}/items/{item_id}")
async def delete_order_item(
    order_id: str,
    item_id: str,
    data: OrderItemDelete,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    try:
        return success(
            await service.mutate_order_item(
                UUID(order_id),
                "delete",
                item_id=UUID(item_id),
                expected_updated_at=data.expected_updated_at,
                reason=data.reason,
                operated_by=current_user.id,
                operated_by_name=current_user.real_name or current_user.username,
                ip_address=request.client.host if request.client else None,
                preview_id=data.preview_id,
                plan_hash=data.plan_hash,
                preview_expires_at=data.preview_expires_at,
                confirm_high_risk=data.confirm_high_risk,
            )
        )
    except OrderItemMutationConflict as e:
        await db.rollback()
        return JSONResponse(status_code=409, content=error(40901, str(e)))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.post("/{order_id}/reopen-completed")
async def reopen_completed_order(
    order_id: str,
    data: OrderStatusChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_SYSTEM_SUPER_ADMIN)),
):
    service = BusinessDocumentService(db, doc_type="order", viewer=current_user)
    oid = UUID(order_id)
    try:
        order = await service.reopen_completed_order(oid, data.reason or "", current_user.id)
    except ValueError as e:
        return error(40001, str(e))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_ORDER, oid, ACTION_STATUS_CHANGE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"status": "in_installation", "reason": data.reason, "action": "reopen_completed"})
    return success(order)


@router.post("/{order_id}/set-cost")
async def set_order_cost(
    order_id: str,
    data: CostEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    try:
        order = await service.set_cost(UUID(order_id), data.cost_amount)
        return success(order)
    except OrderDataMutationLocked as e:
        return error(40001, str(e))
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/auto-cost")
async def auto_calculate_cost(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    try:
        order = await service.auto_calculate_cost(UUID(order_id))
        return success(order)
    except OrderDataMutationLocked as e:
        return error(40001, str(e))
    except ValueError as e:
        return error(40401, str(e))


@router.post("/{order_id}/change-status")
async def change_order_status(
    order_id: str,
    data: OrderStatusChange,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_CHANGE_STATUS)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    oid = UUID(order_id)
    try:
        order = await service.change_status(oid, data.to_status, data.reason, current_user.id)
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_ORDER, oid, ACTION_STATUS_CHANGE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"status": data.to_status, "reason": data.reason})
    return success(order)


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    data: OrderDeleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_all_permissions(PERM_ORDER_DELETE, PERM_ORDER_VIEW_PRICE)),
):
    from app.services.order_management_service import OrderManagementService
    service = OrderManagementService(db, current_user)
    oid = UUID(order_id)
    try:
        return success(await service.delete(oid, data.model_dump()))
    except ValueError as e:
        await db.rollback()
        return error(40001, str(e))


@router.post("/{order_id}/delete-preview")
async def preview_order_delete(order_id: UUID, data: OrderDeleteRequest, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_all_permissions(PERM_ORDER_DELETE, PERM_ORDER_VIEW_PRICE))):
    from app.services.order_management_service import OrderManagementService
    try:
        return success(await OrderManagementService(db, current_user).deletion_preview(order_id, data.model_dump()))
    except ValueError as exc:
        return error(40001, str(exc))


@router.get("/{order_id}/change-actions")
async def order_change_actions(order_id: UUID, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_permission(PERM_ORDER_READ))):
    from app.services.order_management_service import OrderManagementService
    try:
        rows = await OrderManagementService(db, current_user).list_actions(order_id)
        return success(rows)
    except ValueError as exc:
        return error(40401, str(exc))


@router.post("/{order_id}/change-actions/{action_id}/resolve")
async def resolve_order_action(order_id: UUID, action_id: UUID, data: OrderActionResolve,
                               db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_permission(PERM_ORDER_READ))):
    from app.services.order_management_service import OrderManagementService
    try:
        return success(await OrderManagementService(db, current_user).resolve_action(order_id, action_id, data.resolution))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.get("/{order_id}/funds")
async def order_funds(order_id: UUID, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(require_all_permissions(PERM_ORDER_READ, PERM_PAYMENT_READ))):
    from app.services.order_management_service import OrderManagementService
    try:
        return success(await OrderManagementService(db, current_user).funds(order_id))
    except ValueError as exc:
        return error(40401, str(exc))


@router.post("/{order_id}/funds")
async def mutate_order_funds(order_id: UUID, data: OrderFundMutation, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_all_permissions(PERM_ORDER_READ, PERM_PAYMENT_CREATE, PERM_PAYMENT_READ))):
    from app.services.order_management_service import OrderManagementService
    try:
        return success(await OrderManagementService(db, current_user).mutate_funds(order_id, data.model_dump()))
    except ValueError as exc:
        await db.rollback()
        return error(40001, str(exc))


@router.post("/{order_id}/restore")
async def restore_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_DELETE)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    oid = UUID(order_id)
    try:
        order = await service.restore(oid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_ORDER, oid, "restore",
                            ip_address=request.client.host if request.client else None,
                            after_data={"status": "cancelled"})
        return success(order)
    except ValueError as e:
        return error(40401, str(e))


@router.put("/{order_id}/contact")
async def update_order_contact(
    order_id: str,
    data: ContactEntry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_UPDATE)),
):
    raise HTTPException(status_code=410, detail="请使用完整订单编辑页修改联系人并确认关联影响")
