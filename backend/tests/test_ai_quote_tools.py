from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.ai_assistant.tools.quote_tools import (
    create_quote_confirmed,
    preview_quote_creation,
)


@pytest.mark.asyncio
async def test_ai_quote_preview_uses_area_and_all_fees():
    result = await preview_quote_creation(
        db=MagicMock(),
        user=MagicMock(),
        customer_id=str(uuid4()),
        items=[
            {
                "item_name": "门头",
                "width": 200,
                "width_unit": "cm",
                "height": 3,
                "height_unit": "m",
                "pieces": 2,
                "use_area": True,
                "quantity": 1,
                "unit_price": 10,
                "process_fee": 3,
                "installation_fee": 4,
                "design_fee": 5,
                "transport_fee": 6,
                "other_fee": 7,
            }
        ],
    )

    assert result["items"][0]["area"] == 12
    assert result["items"][0]["subtotal"] == 145
    assert result["total_amount"] == 145


@pytest.mark.asyncio
async def test_ai_created_quote_returns_real_quote_number():
    service = MagicMock()
    service.create = AsyncMock(
        return_value={
            "id": str(uuid4()),
            "quote_no": "Q20260730-0001",
            "customer_name": "测试客户",
            "project_name": "测试项目",
            "total_amount": 100,
        }
    )

    with patch(
        "app.services.business_document_service.BusinessDocumentService",
        return_value=service,
    ):
        result = await create_quote_confirmed(
            db=MagicMock(),
            user=MagicMock(),
            customer_id=str(uuid4()),
            project_name="测试项目",
            items=[
                {
                    "item_name": "灯箱",
                    "quantity": 1,
                    "unit_price": 100,
                }
            ],
        )

    assert result["quote_no"] == "Q20260730-0001"
    assert "Q20260730-0001" in result["note"]
