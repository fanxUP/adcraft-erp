"""Pytest fixtures and test utilities for AdCraft ERP backend tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest


# --- Common test data ---

SAMPLE_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_TASK_ID = UUID("22222222-2222-2222-2222-222222222222")
SAMPLE_ORDER_ID = UUID("33333333-3333-3333-3333-333333333333")
SAMPLE_CUSTOMER_ID = UUID("44444444-4444-4444-4444-444444444444")

TEST_USERNAME = "testuser"
TEST_PASSWORD = "TestPass123!"
TEST_NEW_PASSWORD = "NewPass456!"


# --- Mock helpers ---

class MockResult:
    """Mock an async SQLAlchemy result with configurable scalar return."""

    def __init__(self, scalar_return=None, scalars_return=None):
        self._scalar = scalar_return
        self._scalars = scalars_return

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        if self._scalars is not None:
            return self._scalars
        return []


class MockAsyncSession:
    """Mock an async SQLAlchemy session for service-level tests.

    Usage:
        session = MockAsyncSession()
        session.execute_result = "some_value"  # controls scalar_one_or_none
    """

    def __init__(self):
        self.execute_result = None
        self.execute = AsyncMock(side_effect=self._mock_execute)
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()

    async def _mock_execute(self, *args, **kwargs):
        return MockResult(scalar_return=self.execute_result)


@pytest.fixture
def mock_db():
    """Provide a MockAsyncSession that resets between tests."""
    return MockAsyncSession()


# --- Mock model helpers ---

def make_mock_installation_task(
    task_id: UUID = SAMPLE_TASK_ID,
    installation_no: str = "I20260629-0001",
    order_id: UUID = SAMPLE_ORDER_ID,
    customer_id: UUID = SAMPLE_CUSTOMER_ID,
    project_name: str = "测试安装任务",
    status: str = "pending",
    address: str | None = "北京市朝阳区测试路100号",
    contact_name: str | None = "张三",
    contact_phone: str | None = "13800138000",
    scheduled_at: datetime | None = None,
    acceptance_result: str | None = None,
    completed_at: datetime | None = None,
    assigned_to: UUID | None = None,
    attachments: list | None = None,
):
    """Create a mock InstallationTask-like object for tests."""
    now = datetime.now(timezone.utc)
    task = MagicMock()
    task.id = task_id
    task.installation_no = installation_no
    task.order_id = order_id
    task.customer_id = customer_id
    task.project_name = project_name
    task.status = status
    task.address = address
    task.contact_name = contact_name
    task.contact_phone = contact_phone
    task.scheduled_at = scheduled_at or now
    task.acceptance_result = acceptance_result
    task.completed_at = completed_at
    task.assigned_to = assigned_to
    task.attachments = attachments or []
    task.created_at = now
    task.updated_at = now
    return task


def make_mock_design_task(
    task_id: UUID = SAMPLE_TASK_ID,
    design_no: str = "D20260629-0001",
    order_id: UUID = SAMPLE_ORDER_ID,
    customer_id: UUID = SAMPLE_CUSTOMER_ID,
    project_name: str = "测试设计任务",
    status: str = "pending",
    description: str | None = "这是一个测试设计任务",
    design_file_url: str | None = None,
    client_comments: str | None = None,
    completed_at: datetime | None = None,
    assigned_to: UUID | None = None,
    attachments: list | None = None,
):
    """Create a mock DesignTask-like object for tests."""
    now = datetime.now(timezone.utc)
    task = MagicMock()
    task.id = task_id
    task.design_no = design_no
    task.order_id = order_id
    task.customer_id = customer_id
    task.project_name = project_name
    task.status = status
    task.description = description
    task.design_file_url = design_file_url
    task.client_comments = client_comments
    task.completed_at = completed_at
    task.assigned_to = assigned_to
    task.attachments = attachments or []
    task.created_at = now
    task.updated_at = now
    return task


def make_mock_production_task(
    task_id: UUID = SAMPLE_TASK_ID,
    production_no: str = "P20260629-0001",
    order_id: UUID = SAMPLE_ORDER_ID,
    customer_id: UUID = SAMPLE_CUSTOMER_ID,
    project_name: str = "测试制作任务",
    status: str = "pending",
    material_id: UUID | None = None,
    process_id: UUID | None = None,
    length: float | None = 2.5,
    width: float | None = 1.5,
    height: float | None = 0.3,
    quantity: float = 10,
    qc_result: str | None = None,
    rework_reason: str | None = None,
    completed_at: datetime | None = None,
    assigned_to: UUID | None = None,
    attachments: list | None = None,
):
    """Create a mock ProductionTask-like object for tests."""
    now = datetime.now(timezone.utc)
    task = MagicMock()
    task.id = task_id
    task.production_no = production_no
    task.order_id = order_id
    task.customer_id = customer_id
    task.project_name = project_name
    task.status = status
    task.material_id = material_id
    task.process_id = process_id
    task.length = length
    task.width = width
    task.height = height
    task.quantity = quantity
    task.qc_result = qc_result
    task.rework_reason = rework_reason
    task.completed_at = completed_at
    task.assigned_to = assigned_to
    task.attachments = attachments or []
    task.created_at = now
    task.updated_at = now
    return task
