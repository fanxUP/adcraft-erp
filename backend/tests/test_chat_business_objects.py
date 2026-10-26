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
async def test_recent_quotes_are_filtered_by_current_sales_owner():
    user_id, quote_id = uuid4(), uuid4()
    db = AsyncMock()
    db.execute.return_value = rows_result([
        SimpleNamespace(id=quote_id, doc_no="Q-AUDIT", customer_name="AUDIT", status="draft"),
    ])

    result = await conversations.get_my_recent_objects(
        type="quote", limit=10, db=db, current_user=SimpleNamespace(id=user_id),
    )

    assert result["data"][0]["id"] == str(quote_id)
    query = db.execute.await_args.args[0]
    assert "business_documents.sales_user_id" in str(query.whereclause)
    assert user_id in query.compile().params.values()


@pytest.mark.asyncio
async def test_recommendations_include_matching_customer_from_current_schema():
    customer_id = uuid4()
    db = AsyncMock()
    db.execute.side_effect = [
        rows_result([]), rows_result([]),
        rows_result([SimpleNamespace(id=customer_id, name="AUDIT", phone="123")]),
    ]
    repository = MagicMock()
    repository.get_messages = AsyncMock(return_value=[
        SimpleNamespace(content="AUDIT", type="text", extra_data=None),
    ])

    with patch.object(conversations, "MessageRepo", return_value=repository):
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

    with patch.object(conversations, "MessageRepo", return_value=repository):
        result = await conversations.get_recommendations(
            uuid4(), limit=10, current_user=SimpleNamespace(id=uuid4(), roles=[]), db=db,
        )

    assert result["data"] == []
    assert db.execute.await_count == 2
