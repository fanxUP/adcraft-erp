"""AI 安全代操作的确认、权限与并发保护测试。"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Register string-based model relationship targets for isolated tests.
import app.models.customer  # noqa: F401
import app.models.task  # noqa: F401
import app.models.vehicle  # noqa: F401
import pytest
from app.ai_assistant.tool_executor import ToolExecutor
from app.ai_assistant.tool_registry import AiToolDefinition


def _user(*permissions: str):
    role = SimpleNamespace(
        permissions=[SimpleNamespace(code=permission) for permission in permissions],
    )
    return SimpleNamespace(id=uuid4(), roles=[role])


def _executor():
    executor = ToolExecutor(MagicMock())
    executor.audit_logger.log_tool_call = AsyncMock(
        return_value=SimpleNamespace(id=uuid4()),
    )
    executor.audit_logger.update_tool_call_status = AsyncMock()
    executor.audit_logger.log_audit = AsyncMock()
    executor.action_confirm.create_pending_action = AsyncMock(
        return_value=SimpleNamespace(id=uuid4()),
    )
    return executor


def test_every_confirmation_tool_has_a_separate_preview_handler():
    executor = _executor()

    confirmation_tools = [
        tool for tool in executor.registry.list_tools()
        if tool.requires_confirmation
    ]

    assert confirmation_tools
    assert all(tool.preview_handler is not None for tool in confirmation_tools)


@pytest.mark.asyncio
async def test_confirmation_tool_uses_preview_handler_without_writing():
    executor = _executor()
    write_handler = AsyncMock(return_value={"status": "written"})
    preview_handler = AsyncMock(return_value={"action_label": "测试写入"})
    tool_name = f"test_safe_write_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试安全写入",
        parameters={"type": "object", "properties": {}},
        risk_level="level_3",
        requires_confirmation=True,
        handler=write_handler,
        preview_handler=preview_handler,
    ))

    result = await executor.execute_tool(
        tool_name,
        {"business_id": str(uuid4())},
        _user(),
        session_id=uuid4(),
    )

    assert result["status"] == "waiting_confirmation"
    preview_handler.assert_awaited_once()
    write_handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_action_rechecks_permission_before_writing():
    executor = _executor()
    write_handler = AsyncMock(return_value={"status": "written"})
    tool_name = f"test_permission_write_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试权限写入",
        parameters={"type": "object", "properties": {}},
        risk_level="level_3",
        required_permission="order:change_status",
        requires_confirmation=True,
        handler=write_handler,
        preview_handler=AsyncMock(return_value={"action_label": "测试"}),
    ))
    action_id = uuid4()
    owner = _user()
    pending = SimpleNamespace(
        id=action_id,
        user_id=owner.id,
        session_id=uuid4(),
        action_type=tool_name,
        tool_name=tool_name,
        tool_args={},
        preview_data={},
        status="waiting_confirmation",
        expires_at=None,
    )
    executor.action_confirm.get_pending_action = AsyncMock(return_value=pending)
    executor.action_confirm.confirm_action = AsyncMock(return_value=pending)

    result = await executor.execute_confirmed_action(action_id, owner)

    assert result["status"] == "blocked"
    write_handler.assert_not_awaited()
    executor.action_confirm.confirm_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_tool_does_not_misclassify_unexpected_permission_error():
    executor = _executor()
    tool_name = f"test_permission_backend_failure_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试权限后端异常",
        parameters={"type": "object", "properties": {}},
        risk_level="level_1",
        required_permission="order:read",
        handler=AsyncMock(),
    ))
    executor.permission_guard.assert_permission = AsyncMock(
        side_effect=RuntimeError("permission backend unavailable"),
    )

    with pytest.raises(RuntimeError, match="permission backend unavailable"):
        await executor.execute_tool(
            tool_name,
            {},
            _user(),
            session_id=uuid4(),
        )

    executor.audit_logger.log_tool_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_action_does_not_misclassify_unexpected_permission_error():
    executor = _executor()
    tool_name = f"test_confirmed_permission_backend_failure_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试确认动作权限后端异常",
        parameters={"type": "object", "properties": {}},
        risk_level="level_3",
        required_permission="order:change_status",
        handler=AsyncMock(),
    ))
    owner = _user()
    executor.action_confirm.get_pending_action = AsyncMock(
        return_value=SimpleNamespace(
            user_id=owner.id,
            status="waiting_confirmation",
            tool_name=tool_name,
        ),
    )
    executor.permission_guard.assert_permission = AsyncMock(
        side_effect=RuntimeError("permission backend unavailable"),
    )
    executor.action_confirm.confirm_action = AsyncMock()

    with pytest.raises(RuntimeError, match="permission backend unavailable"):
        await executor.execute_confirmed_action(uuid4(), owner)

    executor.action_confirm.confirm_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_tool_handler_failure_returns_failed_and_updates_audit():
    executor = _executor()
    tool_name = f"test_handler_failure_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试工具处理异常",
        parameters={"type": "object", "properties": {}},
        risk_level="level_1",
        handler=AsyncMock(side_effect=RuntimeError("handler failed")),
    ))

    result = await executor.execute_tool(
        tool_name,
        {},
        _user(),
        session_id=uuid4(),
    )

    assert result == {
        "status": "failed",
        "error_message": "handler failed",
    }
    executor.audit_logger.update_tool_call_status.assert_awaited_once()
    assert (
        executor.audit_logger.update_tool_call_status.call_args.kwargs[
            "error_message"
        ]
        == "handler failed"
    )


@pytest.mark.asyncio
async def test_confirmed_action_failure_marks_action_failed():
    executor = _executor()
    tool_name = f"test_confirmed_handler_failure_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试确认动作处理异常",
        parameters={"type": "object", "properties": {}},
        risk_level="level_3",
        required_permission="order:change_status",
        handler=AsyncMock(side_effect=RuntimeError("confirmed handler failed")),
    ))
    owner = _user("order:change_status")
    action_id = uuid4()
    pending = SimpleNamespace(
        id=action_id,
        user_id=owner.id,
        session_id=uuid4(),
        action_type=tool_name,
        tool_name=tool_name,
        tool_args={},
        preview_data={},
        status="waiting_confirmation",
    )
    executor.action_confirm.get_pending_action = AsyncMock(return_value=pending)
    executor.action_confirm.confirm_action = AsyncMock(return_value=pending)
    executor.action_confirm.mark_executed = AsyncMock()

    result = await executor.execute_confirmed_action(action_id, owner)

    assert result == {
        "status": "failed",
        "error_message": "confirmed handler failed",
    }
    executor.action_confirm.mark_executed.assert_awaited_once_with(
        action_id,
        error_message="confirmed handler failed",
    )


@pytest.mark.asyncio
async def test_pending_action_expiry_uses_explicit_naive_utc():
    from app.ai_assistant.action_confirm import ActionConfirmService

    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)
    service = ActionConfirmService(db)

    with patch(
        "app.ai_assistant.action_confirm._utc_now",
        return_value=fixed_now,
    ):
        await service.create_pending_action(
            session_id=uuid4(),
            user_id=uuid4(),
            action_type="test_action",
            tool_name="test_tool",
            tool_args={},
            preview_data={},
        )

    action = db.add.call_args.args[0]
    assert action.expires_at == fixed_now + timedelta(minutes=30)
    assert action.expires_at.tzinfo is None


@pytest.mark.asyncio
async def test_confirm_action_atomically_claims_unexpired_action():
    from app.ai_assistant.action_confirm import ActionConfirmService

    claimed = SimpleNamespace(status="confirmed")
    statement_result = MagicMock()
    statement_result.scalar_one_or_none.return_value = claimed
    db = MagicMock()
    db.execute = AsyncMock(return_value=statement_result)
    db.commit = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)

    with patch(
        "app.ai_assistant.action_confirm._utc_now",
        return_value=fixed_now,
    ):
        result = await ActionConfirmService(db).confirm_action(uuid4(), uuid4())

    assert result is claimed
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_action_marks_expired_action_without_claiming_it():
    from app.ai_assistant.action_confirm import ActionConfirmService

    statement_result = MagicMock()
    statement_result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[statement_result, MagicMock()],
    )
    db.commit = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)

    with patch(
        "app.ai_assistant.action_confirm._utc_now",
        return_value=fixed_now,
    ):
        result = await ActionConfirmService(db).confirm_action(uuid4(), uuid4())

    assert result is None
    assert db.execute.await_count == 2
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_logger_uses_explicit_naive_utc_for_terminal_status():
    from app.ai_assistant.audit_logger import AuditLogger

    log = SimpleNamespace(status="running", finished_at=None, error_message=None)
    db = MagicMock()
    db.get = AsyncMock(return_value=log)
    db.commit = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)

    with patch(
        "app.ai_assistant.audit_logger._utc_now",
        return_value=fixed_now,
    ):
        await AuditLogger(db).update_tool_call_status(
            uuid4(),
            "failed",
            error_message="handler failed",
        )

    assert log.status == "failed"
    assert log.finished_at == fixed_now
    assert log.finished_at.tzinfo is None
    assert log.error_message == "handler failed"


@pytest.mark.asyncio
async def test_cancel_action_records_explicit_naive_utc():
    from app.ai_assistant.action_confirm import ActionConfirmService

    action = SimpleNamespace(status="waiting_confirmation", cancelled_at=None)
    db = MagicMock()
    db.get = AsyncMock(return_value=action)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)

    with patch(
        "app.ai_assistant.action_confirm._utc_now",
        return_value=fixed_now,
    ):
        result = await ActionConfirmService(db).cancel_action(uuid4())

    assert result is action
    assert action.status == "cancelled"
    assert action.cancelled_at == fixed_now
    assert action.cancelled_at.tzinfo is None
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(action)


@pytest.mark.asyncio
async def test_mark_executed_failure_records_explicit_naive_utc():
    from app.ai_assistant.action_confirm import ActionConfirmService

    action = SimpleNamespace(
        status="confirmed",
        executed_at=None,
        error_message=None,
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=action)
    db.commit = AsyncMock()
    fixed_now = datetime(2026, 9, 8, 12, 0)

    with patch(
        "app.ai_assistant.action_confirm._utc_now",
        return_value=fixed_now,
    ):
        await ActionConfirmService(db).mark_executed(
            uuid4(),
            error_message="执行失败",
        )

    assert action.status == "failed"
    assert action.executed_at == fixed_now
    assert action.executed_at.tzinfo is None
    assert action.error_message == "执行失败"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_action_rejects_another_users_action():
    executor = _executor()
    write_handler = AsyncMock(return_value={"status": "written"})
    tool_name = f"test_owned_write_{uuid4().hex}"
    executor.registry.register(AiToolDefinition(
        name=tool_name,
        description="测试操作归属",
        parameters={"type": "object", "properties": {}},
        risk_level="level_3",
        requires_confirmation=True,
        handler=write_handler,
        preview_handler=AsyncMock(return_value={"action_label": "测试"}),
    ))
    pending = SimpleNamespace(
        user_id=uuid4(),
        status="waiting_confirmation",
        tool_name=tool_name,
    )
    executor.action_confirm.get_pending_action = AsyncMock(return_value=pending)

    result = await executor.execute_confirmed_action(uuid4(), _user())

    assert result["status"] == "failed"
    write_handler.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_status_execution_rejects_stale_preview():
    from app.ai_assistant.tools.status_action_tools import execute_order_status_change

    order_id = UUID("33333333-3333-3333-3333-333333333333")
    service = MagicMock()
    service.get_by_id = AsyncMock(return_value={
        "id": str(order_id),
        "doc_no": "ORD-001",
        "status": "designing",
    })
    service.change_status = AsyncMock()

    with patch(
        "app.services.business_document_service.BusinessDocumentService",
        return_value=service,
    ):
        with pytest.raises(ValueError, match="状态已变化"):
            await execute_order_status_change(
                db=MagicMock(),
                user=_user("order:change_status"),
                business_id=str(order_id),
                current_status="confirmed",
                target_status="designing",
            )

    service.change_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_status_preview_returns_readable_effects():
    from app.ai_assistant.tools.status_action_tools import preview_order_status_change

    order_id = UUID("33333333-3333-3333-3333-333333333333")
    service = MagicMock()
    service.get_by_id = AsyncMock(return_value={
        "id": str(order_id),
        "doc_no": "ORD-001",
        "project_name": "门店招牌",
        "status": "designing",
    })

    with patch(
        "app.services.business_document_service.BusinessDocumentService",
        return_value=service,
    ):
        preview = await preview_order_status_change(
            db=MagicMock(),
            user=_user("order:change_status"),
            business_id=str(order_id),
            current_status="designing",
            target_status="in_production",
            reason="设计已确认",
        )

    assert preview["action_label"] == "推进订单状态"
    assert preview["current_status_label"] == "设计中"
    assert preview["target_status_label"] == "生产中"
    assert preview["effects"] == ["创建或衔接生产任务"]


@pytest.mark.asyncio
async def test_design_task_preview_rejects_submission_without_design_file():
    from app.ai_assistant.tools.task_status_action_tools import (
        preview_task_status_change,
    )

    task_id = UUID("55555555-5555-5555-5555-555555555555")
    service = MagicMock()
    service.get_task = AsyncMock(return_value={
        "id": str(task_id),
        "design_no": "DES-001",
        "project_name": "企业文化墙",
        "status": "designing",
        "assigned_to": str(uuid4()),
        "design_file_url": None,
    })

    with patch(
        "app.ai_assistant.tools.task_status_action_tools._get_task_service",
        return_value=service,
    ):
        with pytest.raises(ValueError, match="尚未上传设计稿"):
            await preview_task_status_change(
                db=MagicMock(),
                user=_user("design_task:change_status"),
                task_type="design_task",
                business_id=str(task_id),
                current_status="designing",
                target_status="pending_review",
                order_item_ids=[str(UUID("77777777-7777-7777-7777-777777777777"))],
            )


@pytest.mark.asyncio
async def test_task_status_execution_rejects_stale_preview():
    from app.ai_assistant.tools.task_status_action_tools import (
        execute_task_status_change,
    )

    task_id = UUID("66666666-6666-6666-6666-666666666666")
    service = MagicMock()
    service.get_task = AsyncMock(return_value={
        "id": str(task_id),
        "production_no": "PRO-001",
        "status": "qc_check",
    })
    service.change_status = AsyncMock()

    with patch(
        "app.ai_assistant.tools.task_status_action_tools._get_task_service",
        return_value=service,
    ):
        with pytest.raises(ValueError, match="状态已变化"):
            await execute_task_status_change(
                db=MagicMock(),
                user=_user("production_task:change_status"),
                task_type="production_task",
                business_id=str(task_id),
                current_status="in_progress",
                target_status="qc_check",
            )

    service.change_status.assert_not_awaited()


def test_core_task_status_tools_are_registered_with_scoped_permissions():
    from app.ai_assistant.tool_registry import ToolRegistry
    from app.ai_assistant.tools.task_status_action_tools import (
        register_task_status_action_tools,
    )

    register_task_status_action_tools()
    registry = ToolRegistry()

    expected = {
        "change_design_task_status": "design_task:change_status",
        "change_production_task_status": "production_task:change_status",
        "change_installation_task_status": "installation_task:change_status",
    }
    for tool_name, permission in expected.items():
        tool = registry.get(tool_name)
        assert tool is not None
        assert tool.required_permission == permission
        assert tool.requires_confirmation is True
        assert tool.preview_handler is not None


@pytest.mark.asyncio
async def test_acceptance_preview_rejects_unfinished_items():
    from app.ai_assistant.tools.acceptance_action_tools import (
        preview_acceptance_status_change,
    )

    acceptance_id = UUID("77777777-7777-7777-7777-777777777777")
    service = MagicMock()
    service.get_detail = AsyncMock(return_value={
        "id": str(acceptance_id),
        "acceptance_no": "ACC-001",
        "project_name": "门店招牌",
        "status": "pending",
        "items": [
            {"item_name": "发光字", "item_status": "accepted"},
            {"item_name": "安装", "item_status": "pending"},
        ],
    })

    with patch(
        "app.services.acceptance_service.AcceptanceService",
        return_value=service,
    ):
        with pytest.raises(ValueError, match="仍有 1 项验收明细未确认"):
            await preview_acceptance_status_change(
                db=MagicMock(),
                user=_user("acceptance:change_status"),
                business_id=str(acceptance_id),
                current_status="pending",
                target_status="accepted",
            )


@pytest.mark.asyncio
async def test_acceptance_execution_passes_reason_and_operator():
    from app.ai_assistant.tools.acceptance_action_tools import (
        execute_acceptance_status_change,
    )

    acceptance_id = UUID("88888888-8888-8888-8888-888888888888")
    user = _user("acceptance:change_status")
    service = MagicMock()
    service.get_detail = AsyncMock(return_value={
        "id": str(acceptance_id),
        "acceptance_no": "ACC-002",
        "status": "pending",
        "items": [{"item_name": "灯箱", "item_status": "accepted"}],
    })
    service.change_status = AsyncMock(return_value={
        "id": str(acceptance_id),
        "acceptance_no": "ACC-002",
        "status": "rejected",
    })

    with patch(
        "app.services.acceptance_service.AcceptanceService",
        return_value=service,
    ):
        result = await execute_acceptance_status_change(
            db=MagicMock(),
            user=user,
            business_id=str(acceptance_id),
            current_status="pending",
            target_status="rejected",
            reason="安装位置需整改",
        )

    service.change_status.assert_awaited_once_with(
        acceptance_id,
        "rejected",
        operated_by=user.id,
        reason="安装位置需整改",
    )
    assert result["current_status"] == "rejected"


def test_quote_progress_tools_use_separate_business_permissions():
    from app.ai_assistant.tool_registry import ToolRegistry
    from app.ai_assistant.tools.quote_action_tools import register_quote_action_tools

    register_quote_action_tools()
    registry = ToolRegistry()

    confirm_tool = registry.get("confirm_quote")
    convert_tool = registry.get("convert_quote_to_order")
    assert confirm_tool is not None
    assert confirm_tool.required_permission == "quote:confirm"
    assert confirm_tool.requires_confirmation is True
    assert convert_tool is not None
    assert convert_tool.required_permission == "quote:convert"
    assert convert_tool.requires_confirmation is True


@pytest.mark.asyncio
async def test_quote_conversion_execution_rejects_stale_preview():
    from app.ai_assistant.tools.quote_action_tools import execute_quote_conversion

    quote_id = UUID("99999999-9999-9999-9999-999999999999")
    service = MagicMock()
    service.get_by_id = AsyncMock(return_value={
        "id": str(quote_id),
        "doc_no": "Q20260729-0001",
        "status": "draft",
    })
    service.convert_regular_quote_to_order = AsyncMock()

    with patch(
        "app.services.business_document_service.BusinessDocumentService",
        return_value=service,
    ):
        with pytest.raises(ValueError, match="状态已变化"):
            await execute_quote_conversion(
                db=MagicMock(),
                user=_user("quote:convert"),
                business_id=str(quote_id),
                current_status="confirmed",
            )

    service.convert_regular_quote_to_order.assert_not_awaited()
