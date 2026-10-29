"""Real SQL regressions for the October project audit repairs."""
import os
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import insert

from app.models.task import Attachment, DesignTask
from app.models.order_task_assignee import OrderTaskAssignee
from app.models.employee import Employee
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.chat import Conversation, ConversationMember
from app.models.payment import Expense, Payment
from app.models.payable import PayablePayment
from app.services.file_access_service import can_read_upload
from app.services.number_generator import generate_order_no, generate_employee_no, generate_project_cost_no
from app.services.payable_service import PayableService
from app.services.report_service import ReportService
from tests.test_order_first_integration import fixture_db  # noqa: F401

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not os.getenv("ORDER_FIRST_TEST_URL"), reason="requires isolated PostgreSQL")]


def viewer(user_id, *permissions):
    return SimpleNamespace(id=user_id, roles=[SimpleNamespace(permissions=[SimpleNamespace(code=p) for p in permissions])])


async def test_attachment_private_fields_and_current_conversation_membership(fixture_db):
    db, management, customer = fixture_db
    user_id = management.viewer.id
    db.add(Employee(employee_no="001", name="合成员工", id_card_front_url="/uploads/private.png"))
    conversation = Conversation(id=uuid4(), type="group", name="合成会话")
    db.add(conversation)
    await db.flush()
    db.add(Attachment(related_type="chat_file", related_id=conversation.id, uploaded_by=user_id,
        filename="chat.png", file_path="chat/chat.png"))
    await db.flush()
    assert not await can_read_upload(db, "private.png", viewer(user_id, "employee:read"))
    order = BusinessDocument(doc_type="order", doc_no="FAKE-LINK", project_name="合成引用", order_date=datetime(2026, 10, 29).date(), status="pending_confirm")
    db.add(order)
    await db.flush()
    db.add(BusinessDocumentItem(document_id=order.id, item_name="伪造引用", quantity=1, unit_price=1, subtotal_amount=1, image_url="/uploads/private.png"))
    await db.flush()
    assert not await can_read_upload(db, "private.png", viewer(user_id, "order:read"))
    db.add(Payment(payment_no="PROTECTED-R", customer_id=customer.id, amount=30, payment_method="cash", receipt_url="receipt.png", paid_at=datetime(2026, 10, 29)))
    db.add(BusinessDocumentItem(document_id=order.id, item_name="伪造凭证引用", image_url="/uploads/receipt.png"))
    image_item = BusinessDocumentItem(id=uuid4(), document_id=order.id, item_name="任务样图", image_url="/uploads/task.png")
    employee = Employee(id=uuid4(), employee_no="002", name="任务可见员工", user_id=user_id)
    db.add_all([image_item, employee])
    await db.flush()
    db.add(DesignTask(design_no="AUDIT-D", document_id=order.id, order_item_id=image_item.id, customer_id=customer.id, project_name="合成任务"))
    db.add(OrderTaskAssignee(document_id=order.id, employee_id=employee.id))
    await db.flush()
    assert not await can_read_upload(db, "receipt.png", viewer(user_id, "order:read"))
    assert await can_read_upload(db, "receipt.png", viewer(user_id, "payment:read"))
    assert await can_read_upload(db, "task.png", viewer(user_id, "design_task:read"))
    assert not await can_read_upload(db, "task.png", viewer(uuid4(), "design_task:read"))
    assert await can_read_upload(db, "private.png", viewer(user_id, "employee:read", "employee:private"))
    assert not await can_read_upload(db, "chat/chat.png", viewer(user_id))
    member = ConversationMember(conversation_id=conversation.id, user_id=user_id)
    db.add(member)
    await db.flush()
    assert await can_read_upload(db, "chat/chat.png", viewer(user_id))
    await db.delete(member)
    await db.flush()
    assert not await can_read_upload(db, "chat/chat.png", viewer(user_id, "system:super_admin"))


async def test_numeric_sequence_exceeds_display_width(fixture_db):
    db, _, _ = fixture_db
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    for suffix in ("9999", "10000"):
        db.add(BusinessDocument(doc_type="order", doc_no=f"O{today}-{suffix}", project_name="合成边界", order_date=datetime(2026, 10, 29).date(), status="pending_confirm"))
    db.add_all([Employee(employee_no="999", name="合成1"), Employee(employee_no="1000", name="合成2")])
    from app.models.project_cost import ProjectCost
    for suffix in ("999", "1000"):
        db.add(ProjectCost(cost_no=f"{today[2:]}-{suffix}", category="测试", amount=1))
    await db.flush()
    assert await generate_order_no(db) == f"O{today}-10001"
    assert await generate_employee_no(db) == "1001"
    assert await generate_project_cost_no(db) == f"{today[2:]}-1001"


async def test_cashflow_includes_fractional_last_second_but_not_next_day(fixture_db):
    db, _, customer = fixture_db
    for no, amount, at in (("T-1", 100, datetime(2026, 10, 29, 12)),
                           ("T-2", 30, datetime(2026, 10, 29, 23, 59, 59, 500000)),
                           ("T-3", 90, datetime(2026, 10, 30))):
        db.add(Payment(payment_no=no, customer_id=customer.id, amount=amount, payment_method="cash", paid_at=at))
    await db.flush()
    assert await ReportService(db)._sum_payments(datetime(2026, 10, 29), datetime(2026, 10, 30)) == 130


async def test_payable_sql_paging_filter_and_voided_payment(fixture_db):
    db, _, _ = fixture_db
    ids = [uuid4() for _ in range(3)]
    for index, source_id in enumerate(ids):
        db.add(Expense(id=source_id, expense_no=f"PAGE-{index}", amount=100, payable_amount=100,
            expense_date=datetime(2026, 10, index + 1), category="合成分页", payee_name="测试供应商"))
    await db.flush()
    db.add(PayablePayment(source_type="expense", source_id=ids[1], payment_no="PAGE-P1", amount=40,
        payment_method="cash", paid_at=datetime(2026, 10, 3)))
    db.add(PayablePayment(source_type="expense", source_id=ids[1], payment_no="PAGE-P2", amount=60,
        payment_method="cash", paid_at=datetime(2026, 10, 3), is_voided=True))
    await db.flush()
    service = PayableService(db)
    rows, total = await service.list_payables(1, 1, keyword="合成分页")
    assert total == 3 and [row["source_id"] for row in rows] == [str(ids[2])]
    rows, total = await service.list_payables(2, 1, keyword="合成分页")
    assert total == 3 and [row["source_id"] for row in rows] == [str(ids[1])]
    rows, total = await service.list_payables(1, 20, status="partial")
    assert total == 1 and rows[0]["remaining_amount"] == 60
    assert (await service.list_payables(1, 20, keyword="%"))[1] == 0
