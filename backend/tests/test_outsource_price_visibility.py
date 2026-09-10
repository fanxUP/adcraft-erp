"""Regression tests for external-task financial field visibility."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.outsource_service import OutsourceService


def make_viewer(*permission_codes: str):
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    role = SimpleNamespace(permissions=permissions)
    return SimpleNamespace(roles=[role])


def make_task():
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        task_no="OT20260910-0001",
        vendor_id=uuid4(),
        related_doc_id=uuid4(),
        related_doc_type="order",
        order_item_id=uuid4(),
        order_item=SimpleNamespace(item_name="标识牌"),
        source_task_type="production",
        source_task_id=uuid4(),
        task_type="production",
        description="外协制作",
        quantity=3,
        unit_price=120,
        total_amount=360,
        paid_amount=0,
        unpaid_amount=360,
        status="in_progress",
        expected_at=now,
        completed_at=None,
        remark=None,
        created_at=now,
        deleted_at=None,
    )


def test_outsource_task_hides_financial_fields_without_cost_permission():
    service = OutsourceService(AsyncMock(), viewer=make_viewer())

    result = service._task_to_dict(make_task(), "供应商A", "项目A")

    assert result["quantity"] == 3.0
    for field in ("unit_price", "total_amount", "paid_amount", "unpaid_amount"):
        assert field not in result


def test_outsource_task_keeps_financial_fields_with_explicit_cost_permission():
    service = OutsourceService(
        AsyncMock(),
        viewer=make_viewer("finance:view_cost"),
    )

    result = service._task_to_dict(make_task(), "供应商A", "项目A")

    assert result["unit_price"] == 120.0
    assert result["total_amount"] == 360.0
    assert result["unpaid_amount"] == 360.0


@pytest.mark.asyncio
async def test_outsource_payment_summary_is_returned_and_redacted_without_cost_permission():
    task = make_task()
    payment = SimpleNamespace(
        id=uuid4(),
        payment_no="OP20260910-0001",
        amount=100,
        payment_method="转账",
        payee_company_name="供应商A",
        paid_at=datetime.now(timezone.utc),
        remark=None,
        created_at=datetime.now(timezone.utc),
    )
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [payment]),
    )
    service = OutsourceService(db, viewer=make_viewer())
    service.task_repo.get_by_id = AsyncMock(return_value=task)
    service._vendor_name = AsyncMock(return_value="供应商A")
    service._related_project_name = AsyncMock(return_value="项目A")

    result = await service.get_task_payment_summary(task.id)

    assert result is not None
    for field in ("total_amount", "paid_amount", "unpaid_amount"):
        assert field not in result
    assert result["payments"] == [{
        "id": str(payment.id),
        "payment_no": payment.payment_no,
        "payment_method": payment.payment_method,
        "payee_company_name": payment.payee_company_name,
        "paid_at": payment.paid_at.isoformat(),
        "remark": payment.remark,
        "created_at": payment.created_at.isoformat(),
    }]
