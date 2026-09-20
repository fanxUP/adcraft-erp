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
    require_permission,
)
from app.models.user import User
from app.schemas.order import (
    OrderItemCreate,
    OrderItemDelete,
    OrderEditRequest,
    OrderItemMutationPreview,
    OrderItemUpdate,
    OrderStatusChange,
    OrderTaskAssigneesUpdate,
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


@router.get("/recycle/list")
async def list_deleted_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_DELETE)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    orders, total = await service.list_deleted(page, page_size, keyword=keyword)
    return success_paginated(orders, total, page, page_size)


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
        return error(40001, str(e))
    await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                        OBJ_ORDER, oid, ACTION_STATUS_CHANGE,
                        ip_address=request.client.host if request.client else None,
                        after_data={"status": data.to_status, "reason": data.reason})
    return success(order)


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_ORDER_DELETE)),
):
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    oid = UUID(order_id)
    try:
        await service.delete(oid)
        await log_operation(db, current_user.id, current_user.real_name or current_user.username,
                            OBJ_ORDER, oid, ACTION_DELETE,
                            ip_address=request.client.host if request.client else None)
        return success({"message": "订单已移入回收站"})
    except ValueError as e:
        return error(40001, str(e))


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
    service = BusinessDocumentService(db, doc_type='order', viewer=current_user)
    try:
        order = await service.update_order_contact(
            UUID(order_id), data.contact_person, data.contact_phone
        )
        return success(order)
    except OrderDataMutationLocked as e:
        return error(40001, str(e))
    except ValueError as e:
        return error(40401, str(e))
