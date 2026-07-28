from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.admin import force_relogin


@pytest.mark.asyncio
async def test_force_relogin_increments_active_user_token_versions():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    response = await force_relogin(db=db, current_user=MagicMock())

    statement = db.execute.await_args.args[0]
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "UPDATE users" in sql
    assert "token_version=(users.token_version + 1)" in sql
    assert "users.deleted_at IS NULL" in sql
    assert "users.is_active IS true" in sql
    db.commit.assert_awaited_once()
    assert response["code"] == 0
    assert response["data"]["message"] == "已强制所有用户重新登录"
