"""Selection authorization cannot be bypassed with alternate JSON media types."""
import json
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.payments import exp_router
from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.company_account_service import require_account_selection
from tests.test_expenditure_service import viewer


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", [None, "application/json", "application/vnd.adcraft+json"])
async def test_payment_account_selection_requires_its_own_permission(content_type):
    app = FastAPI()
    app.include_router(exp_router)
    app.dependency_overrides[get_current_user] = lambda: viewer("expense:create")
    async def database():
        yield None  # No real database access is possible in this API check.
    app.dependency_overrides[get_db] = database
    headers = {"content-type": content_type} if content_type else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/expenses/", headers=headers, content=json.dumps({
            "amount": 100, "payment_account_id": str(uuid4()),
        }))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_empty_json_body_does_not_break_existing_bodyless_actions():
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: viewer("expense:update")
    @app.post("/empty", dependencies=[Depends(require_account_selection)])
    async def empty():
        return {"ok": True}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/empty", headers={"content-type": "application/json"})
    assert response.status_code == 200
