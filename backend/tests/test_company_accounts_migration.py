"""Dry-run the additive migration on populated disposable schema data."""
import os
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, insert, select, text

from app.models.company_account import CompanyAccount
from app.models.outsource import OutsourcePayment
from app.models.payable import PayablePayment
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.models.user import Permission, Role, role_permissions
from tests.test_expenditure_integration import fixture_db  # noqa: F401

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    not os.getenv("EXPENDITURE_TEST_URL"), reason="requires explicitly isolated PostgreSQL",
)]


async def test_migration_preserves_rows_and_sums_grants_and_guarded_rollback(fixture_db):
    db, _, _ = fixture_db
    models = (Expense, ProjectCost, PayablePayment, OutsourcePayment)
    before = [(await db.execute(select(func.count(), func.sum(model.amount)).select_from(model))).one() for model in models]
    for model in models:
        await db.execute(text(f'ALTER TABLE "{model.__tablename__}" DROP COLUMN payment_account_id'))
    await db.execute(text("DROP TABLE company_accounts"))
    operator, reader, finance = uuid4(), uuid4(), uuid4()
    create_permission = uuid4()
    await db.execute(insert(Role).values(id=operator, name="custom_payment_operator"))
    await db.execute(insert(Role).values(id=reader, name="custom_reader"))
    await db.execute(insert(Role).values(id=finance, name="finance"))
    await db.execute(insert(Permission).values(id=create_permission, code="expense:create", name="创建支出"))
    await db.execute(insert(role_permissions).values(role_id=operator, permission_id=create_permission))
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    spec = spec_from_file_location("company_accounts_migration", Path(__file__).parents[1] / "alembic/versions/cca01_company_accounts.py")
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    connection = await db.connection()
    def run(sync_connection, action):
        with Operations.context(MigrationContext.configure(sync_connection)):
            action()
    await connection.run_sync(run, migration.upgrade)
    after = [(await db.execute(select(func.count(), func.sum(model.amount)).select_from(model))).one() for model in models]
    assert after == before
    assert await db.scalar(select(func.count()).select_from(CompanyAccount)) == 0
    for model in models:
        assert await db.scalar(select(func.count()).select_from(model).where(model.payment_account_id.is_not(None))) == 0
    grants = (await db.execute(select(role_permissions.c.role_id, Permission.code).join(Permission, Permission.id == role_permissions.c.permission_id))).all()
    assert (operator, "company_account:select") in grants
    assert (operator, "company_account:manage") not in grants
    assert all(role_id != reader for role_id, _ in grants)
    assert len([code for role_id, code in grants if role_id == finance]) == 4
    # Empty structures can be rolled back and upgraded again without modifying money.
    await connection.run_sync(run, migration.downgrade)
    await connection.run_sync(run, migration.upgrade)
    await db.execute(insert(CompanyAccount).values(name="保留真实账户", account_type="cash"))
    with pytest.raises(Exception, match="Company accounts exist"):
        async with connection.begin_nested():
            await connection.run_sync(run, migration.downgrade)
    assert await db.scalar(select(func.count()).select_from(CompanyAccount)) == 1
