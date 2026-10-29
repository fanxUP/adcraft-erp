"""Chat business lookups must use the current unified document/customer fields."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import app.models.vehicle  # noqa: F401 - register Attachment.vehicle for isolated execution
from app.api import conversations


def rows_result(rows):
    result = MagicMock()
    result.unique.return_value = result
    result.scalars.return_value = result
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_retired_quotes_are_not_returned_by_recent_lookup():
    user_id, quote_id = uuid4(), uuid4()
    db = AsyncMock()
    db.execute.return_value = rows_result([
        SimpleNamespace(id=quote_id, doc_no="Q-AUDIT", customer_name="AUDIT", status="draft"),
    ])

    result = await conversations.get_my_recent_objects(
        type="quote", limit=10, db=db, current_user=SimpleNamespace(id=user_id),
    )

    assert result["data"] == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_recommendations_include_matching_customer_from_current_schema():
    customer_id = uuid4()
    db = AsyncMock()
    db.execute.return_value = rows_result([SimpleNamespace(id=customer_id, name="AUDIT", phone="123")])
    repository = MagicMock()
    repository.get_messages = AsyncMock(return_value=[
        SimpleNamespace(content="AUDIT", type="text", extra_data=None),
    ])

    with patch.object(conversations, "MessageRepo", return_value=repository), patch.object(conversations, "_require_member", new=AsyncMock()):
        result = await conversations.get_recommendations(
            uuid4(), limit=10, current_user=SimpleNamespace(
                id=uuid4(), roles=[SimpleNamespace(permissions=[SimpleNamespace(code="customer:read")])],
            ), db=db,
        )

    assert result["data"] == [{
        "id": str(customer_id), "type": "customer", "title": "客户: AUDIT",
        "subtitle": "联系电话: 123", "status": None,
    }]


@pytest.mark.asyncio
async def test_recommendations_do_not_query_customers_without_customer_read():
    db = AsyncMock()
    db.execute.side_effect = [rows_result([]), rows_result([])]
    repository = MagicMock()
    repository.get_messages = AsyncMock(return_value=[
        SimpleNamespace(content="AUDIT", type="text", extra_data=None),
    ])

    with patch.object(conversations, "MessageRepo", return_value=repository), patch.object(conversations, "_require_member", new=AsyncMock()):
        result = await conversations.get_recommendations(
            uuid4(), limit=10, current_user=SimpleNamespace(id=uuid4(), roles=[]), db=db,
        )

    assert result["data"] == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_nonmember_recommendations_never_read_messages():
    from fastapi import HTTPException
    db = AsyncMock()
    with patch.object(conversations, "ChatService") as service, patch.object(conversations, "MessageRepo") as repository:
        service.return_value.member_repo.is_member = AsyncMock(return_value=False)
        with pytest.raises(HTTPException) as caught:
            await conversations.get_recommendations(uuid4(), limit=10, current_user=SimpleNamespace(id=uuid4()), db=db)
        assert caught.value.status_code == 403
        repository.assert_not_called()


@pytest.mark.asyncio
async def test_card_lookup_requires_business_permission_before_db_read():
    db = AsyncMock()
    assert await conversations._get_card_data(db, "order", uuid4(), viewer=SimpleNamespace(id=uuid4(), roles=[])) is None
    db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_reply_cannot_read_a_different_conversation():
    from app.services.chat_service import ChatService
    from app.schemas.conversation import MessageCreate
    service = ChatService(AsyncMock())
    service.member_repo.is_member = AsyncMock(return_value=True)
    service.message_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(conversation_id=uuid4(), deleted_at=None))
    service.message_repo.create = AsyncMock()
    with pytest.raises(ValueError, match="不属于当前会话"):
        await service.send_message(uuid4(), uuid4(), MessageCreate(type="reply", content="reply", reply_to_id=uuid4()))
    service.message_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_historical_card_is_reauthorized_without_mutating_stored_title():
    from app.schemas.conversation import MessageResponse
    from datetime import datetime
    message = MessageResponse(id=uuid4(), conversation_id=uuid4(), sender_id=uuid4(), type="card",
        content="protected title", created_at=datetime(2026, 10, 29),
        extra_data={"card_type": "order", "card_id": str(uuid4()), "title": "protected title", "amount": 100})
    result = await conversations._visible_chat_message(AsyncMock(), message, SimpleNamespace(id=uuid4(), roles=[]))
    assert result["extra_data"] == {}
    assert result["content"] == "业务资料已停用或无权查看"
    assert message.content == "protected title"


@pytest.mark.asyncio
async def test_batch_card_keeps_client_shape_after_permission_filtering():
    from app.schemas.conversation import MessageResponse
    from datetime import datetime
    message = MessageResponse(id=uuid4(), conversation_id=uuid4(), sender_id=uuid4(), type="card",
        content="old private titles", created_at=datetime(2026, 10, 29), extra_data={"card_type": "batch", "count": 2,
        "cards": [{"card_type": "order", "card_id": str(uuid4())}, {"card_type": "quote", "card_id": str(uuid4())}]})
    with patch.object(conversations, "_get_card_data", new=AsyncMock(side_effect=[{"title": "visible"}, None])):
        result = await conversations._visible_chat_message(AsyncMock(), message, SimpleNamespace(id=uuid4(), roles=[]))
    assert result["extra_data"]["card_type"] == "batch"
    assert result["extra_data"]["count"] == 1
    assert len(result["extra_data"]["cards"]) == 1
    assert "old private titles" not in result["content"]
