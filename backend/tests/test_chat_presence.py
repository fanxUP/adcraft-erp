"""Exercise presence routing and fanout without touching a real database."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api import conversations
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.conversation import UserPresenceResponse
from app.services import chat_service, notification_service


@pytest.fixture(params=["chat", "notifications"])
def connection_manager(request):
    if request.param == "chat":
        return (
            chat_service, chat_service.register_chat_ws,
            chat_service.unregister_chat_ws, chat_service._chat_ws_connections,
        )
    return (
        notification_service, notification_service.register_ws,
        notification_service.unregister_ws, notification_service._ws_connections,
    )


@pytest.mark.asyncio
async def test_presence_update_reaches_presence_endpoint():
    user_id = uuid4()
    application = FastAPI()
    application.include_router(conversations.router, prefix="/api/v1")
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    application.dependency_overrides[get_db] = lambda: AsyncMock()
    service = MagicMock()
    service.update_presence = AsyncMock(
        return_value=UserPresenceResponse(user_id=user_id, status="away"),
    )
    with patch.object(conversations, "ChatService", return_value=service), patch.object(
        conversations, "broadcast_presence_update", new_callable=AsyncMock,
    ) as broadcast:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test",
        ) as client:
            response = await client.put("/api/v1/conversations/presence", json={"status": "away"})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "away"
    service.update_presence.assert_awaited_once_with(user_id, "away")
    service.update_conversation.assert_not_called()
    broadcast.assert_awaited_once_with(user_id, "away")


@pytest.mark.asyncio
async def test_presence_fanout_notifies_shared_members_once_and_excludes_sender():
    sender_id, recipient_id = uuid4(), uuid4()
    service = MagicMock()
    service.member_repo.get_conversation_ids_by_user = AsyncMock(return_value=[uuid4(), uuid4()])
    service.member_repo.get_members = AsyncMock(return_value=[
        SimpleNamespace(user_id=sender_id), SimpleNamespace(user_id=recipient_id),
    ])
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=AsyncMock())
    session.__aexit__ = AsyncMock(return_value=False)
    with patch("app.core.database.AsyncSessionLocal", return_value=session), patch.object(
        conversations, "ChatService", return_value=service,
    ), patch.object(conversations, "broadcast_to_user", new_callable=AsyncMock) as broadcast:
        await conversations.broadcast_presence_update(sender_id, "busy")

    broadcast.assert_awaited_once_with(recipient_id, {
        "type": "presence_update", "data": {"user_id": str(sender_id), "status": "busy"},
    })


@pytest.mark.asyncio
async def test_fanout_tolerates_a_connection_disconnecting_during_send(connection_manager):
    service, _register, unregister, registry = connection_manager
    user_id = uuid4()
    first, second = MagicMock(), MagicMock()
    connections = {first, second}

    async def disconnect_while_sending(_message):
        unregister(user_id, first)
        unregister(user_id, second)

    first.send_text = AsyncMock(side_effect=disconnect_while_sending)
    second.send_text = AsyncMock(side_effect=disconnect_while_sending)
    registry[user_id] = connections
    try:
        await service.broadcast_to_user(user_id, {"type": "presence_update"})
        assert first.send_text.await_count + second.send_text.await_count >= 1
    finally:
        registry.pop(user_id, None)


@pytest.mark.asyncio
async def test_fanout_cleans_failed_connection_after_unregister(connection_manager):
    service, register, unregister, registry = connection_manager
    user_id = uuid4()
    socket = MagicMock()

    async def fail_after_unregister(_message):
        unregister(user_id, socket)
        raise RuntimeError("connection closed")

    socket.send_text = AsyncMock(side_effect=fail_after_unregister)
    register(user_id, socket)
    try:
        await service.broadcast_to_user(user_id, {"type": "presence_update"})
        assert user_id not in registry
    finally:
        registry.pop(user_id, None)
