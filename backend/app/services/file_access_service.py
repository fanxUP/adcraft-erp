"""Authorize legacy upload URLs against their current business references.

Paths remain stable for historical data and printing. No directory-level grant
is inferred from a file name. Unidentified historical files are admin-only.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import literal, or_, select, union_all

from app.core.config import settings
from app.core.file_security import confined_path
from app.core.permissions import user_has_permission
from app.models.task import Attachment, DesignTask, ProductionTask, InstallationTask
from app.services.order_task_assignment_service import get_visible_task, task_visibility_clause


async def register_upload(db, path, user, permission, *, conversation_id=None):
    """Record an unbound upload for its author's preview, or a chat file owner."""
    relative = Path(path).resolve().relative_to(Path(settings.LOCAL_UPLOAD_DIR).resolve()).as_posix()
    row = Attachment(
        related_type="chat_file" if conversation_id else "upload_draft",
        related_id=conversation_id or user.id, uploaded_by=user.id,
        filename=Path(path).name, file_path=relative, category=permission,
        file_size=Path(path).stat().st_size,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(row)
    await db.flush()


async def can_read_upload(db, relative, viewer):
    from app.models.employee import Employee
    from app.models.payment import Payment, Expense
    from app.models.payable import PayablePayment
    from app.models.project_cost import ProjectCost
    from app.models.business_document import BusinessDocument, BusinessDocumentItem
    from app.models.acceptance import AcceptanceAttachment, AcceptanceForm, AcceptanceItem
    from app.models.contract import Contract
    from app.models.framework_contract import FrameworkContractProject
    from app.models.vehicle import VehicleAttachment, VehicleFuelRecord, VehicleCertificate
    from app.models.aerial import (AerialPersonnel, AerialLedgerAttachment,
        AerialPersonnelAttachment, AerialVehicleAttachment, AerialPersonnelExpense, AerialVehicleCost)
    from app.models.chat import ConversationMember

    def permitted(code):
        return user_has_permission(viewer, code)

    variants = (relative, "/uploads/" + relative, "uploads/" + relative,
                confined_path(settings.LOCAL_UPLOAD_DIR, relative))

    async def exists(model, column, *conditions):
        return await db.scalar(select(model.id).where(column.in_(variants), *conditions).limit(1)) is not None

    rows = (await db.execute(select(Attachment).where(Attachment.file_path.in_(variants)))).scalars().all()
    # Client-editable image/receipt URL fields cannot transfer private HR or
    # chat ownership. These authoritative upload records take precedence.
    private_employee = any(att.related_type == "employee" or (
        att.related_type == "upload_draft" and att.category == "employee:private") for att in rows)
    if not private_employee:
        private_employee = await exists(Employee, Employee.id_card_front_url) or await exists(Employee, Employee.id_card_back_url)
    if private_employee and not permitted("employee:private"):
        return False
    chat_rows = [att for att in rows if att.related_type == "chat_file"]
    if chat_rows:
        return await db.scalar(select(ConversationMember.id).where(
            ConversationMember.conversation_id.in_([att.related_id for att in chat_rows]),
            ConversationMember.user_id == viewer.id).limit(1)) is not None
    if relative.startswith("chat/"):
        return permitted("system:super_admin")
    # Financial and signed-document files cannot be declassified by copying a
    # URL into a vehicle/photo/other user-editable field. Query together to
    # avoid one round trip per possible owner on image-heavy pages.
    protected = (
        (Payment, Payment.receipt_url, "payment:read"),
        (Expense, Expense.receipt_url, "expense:read"),
        (ProjectCost, ProjectCost.receipt_url, "expense:read"),
        (PayablePayment, PayablePayment.receipt_url, "expense:read"),
        (Contract, Contract.attachment_path, "contract:read"),
        (FrameworkContractProject, FrameworkContractProject.attachment_path, "contract:read"),
    )
    required = (await db.execute(union_all(*(
        select(literal(permission)).where(column.in_(variants))
        for model, column, permission in protected
    )))).scalars().all()
    if required:
        return all(permitted(permission) for permission in set(required))
    for att in rows:
        if att.related_type == "chat_file":
            if await db.scalar(select(ConversationMember.id).where(ConversationMember.conversation_id == att.related_id, ConversationMember.user_id == viewer.id).limit(1)):
                return True
        elif att.related_type == "upload_draft":
            created = att.created_at.replace(tzinfo=None)
            if (att.uploaded_by == viewer.id and permitted(att.category)
                    and created > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)):
                return True
        elif att.order_id and att.stage:
            from app.services.order_task_attachment_service import OrderTaskAttachmentService, STAGE_CONFIG
            task_id = None
            model = STAGE_CONFIG[att.stage]["model"]
            if not permitted("order:read"):
                task_id = await db.scalar(select(model.id).where(model.document_id == att.order_id, task_visibility_clause(model, viewer)).limit(1))
            try:
                await OrderTaskAttachmentService(db)._authorize(att.order_id, att.stage, viewer, operation="read", task_id=task_id)
                return True
            except (ValueError, PermissionError):
                pass
        elif att.related_type in {"design_task", "production_task", "installation_task"}:
            model = {"design_task": DesignTask, "production_task": ProductionTask, "installation_task": InstallationTask}[att.related_type]
            if permitted(att.related_type + ":read") and await get_visible_task(db, model, att.related_id, viewer):
                return True
        else:
            rule = {"employee": (Employee, "employee:private"), "expense": (Expense, "expense:read"),
                    "project_cost": (ProjectCost, "expense:read")}.get(att.related_type)
            if rule and permitted(rule[1]):
                owner = await db.get(rule[0], att.related_id)
                if owner and owner.deleted_at is None:
                    return True
            if att.related_type == "vehicle" and permitted("vehicle:read"):
                return True

    # An already-owned attachment cannot be made readable by pasting its URL
    # into some other business object with weaker permissions.
    if any(att.related_type != "upload_draft" for att in rows):
        return False

    # Columns with their own business read permission. Check soft deletion on
    # the owning row; task and chat scope is handled separately below.
    rules = [
        (Employee, Employee.id_card_front_url, "employee:private"),
        (Employee, Employee.id_card_back_url, "employee:private"),
        (Payment, Payment.receipt_url, "payment:read"),
        (Expense, Expense.receipt_url, "expense:read"),
        (ProjectCost, ProjectCost.receipt_url, "expense:read"),
        (PayablePayment, PayablePayment.receipt_url, "expense:read"),
        (Contract, Contract.attachment_path, "contract:read"),
        (FrameworkContractProject, FrameworkContractProject.attachment_path, "contract:read"),
        (VehicleAttachment, VehicleAttachment.file_url, "vehicle:read"),
        (VehicleFuelRecord, VehicleFuelRecord.receipt_url, "vehicle:read"),
        (VehicleCertificate, VehicleCertificate.file_url, "vehicle:read"),
        (AerialPersonnel, AerialPersonnel.id_card_front_url, "aerial:read"),
        (AerialPersonnel, AerialPersonnel.id_card_back_url, "aerial:read"),
        (AerialPersonnelAttachment, AerialPersonnelAttachment.file_url, "aerial:read"),
        (AerialVehicleAttachment, AerialVehicleAttachment.file_url, "aerial:read"),
        (AerialLedgerAttachment, AerialLedgerAttachment.file_url, "aerial:read"),
        (AerialPersonnelExpense, AerialPersonnelExpense.receipt_url, "aerial:read"),
        (AerialVehicleCost, AerialVehicleCost.receipt_url, "aerial:read"),
    ]
    for model, column, permission in rules:
        if permitted(permission) and await exists(model, column, *([model.deleted_at.is_(None)] if hasattr(model, "deleted_at") else [])):
            return True

    if permitted("order:read"):
        if await db.scalar(select(BusinessDocumentItem.id).join(BusinessDocument).where(
            BusinessDocumentItem.image_url.in_(variants), BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None)).limit(1)):
            return True
    # Execution users see only images of the work units available to them.
    from app.models.task_order_item_link import TaskOrderItemLink
    for kind, model in (("design", DesignTask), ("production", ProductionTask), ("installation", InstallationTask)):
        if not permitted(kind + "_task:read"):
            continue
        if await db.scalar(select(BusinessDocumentItem.id).join(BusinessDocument).join(
            model, model.document_id == BusinessDocument.id).outerjoin(TaskOrderItemLink,
            (TaskOrderItemLink.task_id == model.id) & (TaskOrderItemLink.task_type == kind)
            & (TaskOrderItemLink.order_item_id == BusinessDocumentItem.id)
            & (TaskOrderItemLink.link_status == "active")).where(
            BusinessDocumentItem.image_url.in_(variants), BusinessDocument.deleted_at.is_(None),
            task_visibility_clause(model, viewer),
            or_(TaskOrderItemLink.id.is_not(None), model.order_item_id == BusinessDocumentItem.id)).limit(1)):
            return True
    if permitted("acceptance:read"):
        for model, column in ((AcceptanceAttachment, AcceptanceAttachment.filepath), (AcceptanceItem, AcceptanceItem.image_url)):
            if await db.scalar(select(model.id).join(AcceptanceForm).where(column.in_(variants), AcceptanceForm.deleted_at.is_(None)).limit(1)):
                return True
    if permitted("design_task:read") and await db.scalar(select(DesignTask.id).where(
        DesignTask.design_file_url.in_(variants), task_visibility_clause(DesignTask, viewer)).limit(1)):
        return True
    # A pasted URL in message text cannot create a file permission. Historical
    # files without reliable ownership remain available only for admin review.
    if any(att.related_type == "chat_file" for att in rows):
        return False
    return permitted("system:super_admin")
