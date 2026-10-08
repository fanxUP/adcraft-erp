"""Real persistence and lifecycle regression in a disposable PostgreSQL schema."""
import importlib
import os
import pkgutil
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import app.models
from app.models.base import Base
from app.services.outsource_service import OutsourceService
from app.services.supplier_service import SupplierService


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("SUPPLIER_MIGRATION_TEST_URL"), reason="requires isolated PostgreSQL")
async def test_shared_supplier_and_historical_tasks_survive_capability_removal_and_deactivation():
    for module in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module.name}")
    schema = "supplier_lifecycle_" + uuid4().hex
    url = os.environ["SUPPLIER_MIGRATION_TEST_URL"].replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as db:
            svc = SupplierService(db)
            shared = await svc.create_supplier(dict(name="测试多业务公司", supplier_types=["material", "outsource"], service_types=["production", "installation"], bank_account="test-account"))
            supplier_id = UUID(shared["id"])
            await db.commit()
            material, _ = await svc.list_suppliers(1, 20, supplier_type="material")
            external, _ = await svc.list_suppliers(1, 20, supplier_type="outsource")
            assert material[0]["id"] == external[0]["id"] == shared["id"]
            outsource = OutsourceService(db)
            vendors, total = await outsource.list_vendors(1, 20, service_type="installation")
            assert total == 1 and vendors[0]["id"] == shared["id"]
            restricted_user = SimpleNamespace(roles=[SimpleNamespace(permissions=[SimpleNamespace(code=code) for code in (
                "outsource_center:read", "outsource_vendor:read", "outsource_vendor:create", "outsource_vendor:update",
            )])])
            scoped = SupplierService(db, viewer=restricted_user)
            restricted_rows, _ = await scoped.list_suppliers(1, 20)
            assert restricted_rows[0]["bank_account"] is None
            await scoped.update_supplier(supplier_id, {"phone": "test-contact"})
            assert (await svc.get_supplier(supplier_id))["bank_account"] == "test-account"
            with pytest.raises(ValueError, match="业务类型"):
                await scoped.update_supplier(supplier_id, {"supplier_types": ["outsource"]})
            with pytest.raises(ValueError, match="其他业务"):
                await scoped.deactivate_supplier(supplier_id)
            legacy_created = await scoped.create_supplier({"name": "仅外协档案"})
            assert legacy_created["supplier_types"] == ["outsource"]
            await scoped.deactivate_supplier(UUID(legacy_created["id"]))
            with pytest.raises(ValueError, match="业务类型"):
                await scoped.create_supplier({"name": "越权材料档案", "supplier_types": ["material"]})
            task = await outsource.create_task(dict(vendor_id=shared["id"], task_type="production", quantity=1, unit_price=100))
            task_id = UUID(task["id"])
            await svc.update_supplier(supplier_id, {"supplier_types": ["material"]})
            await db.commit()
            assert (await outsource.list_vendors(1, 20))[1] == 0
            with pytest.raises(ValueError, match="外协服务"):
                await outsource.create_task(dict(vendor_id=shared["id"], task_type="production"))
            edited = await outsource.update_task(task_id, {"remark": "历史任务继续履约"})
            assert edited["vendor_id"] == shared["id"]
            await svc.deactivate_supplier(supplier_id)
            payment = await outsource.create_payment(dict(vendor_id=shared["id"], task_id=task["id"], amount=40))
            assert payment["amount"] == 40
            summary = await outsource.get_task_payment_summary(task_id)
            assert summary["unpaid_amount"] == 60
            assert (await svc.list_suppliers(1, 20))[1] == 0
            assert (await svc.list_suppliers(1, 20, is_active=None))[1] == 2
            with pytest.raises(ValueError, match="停用"):
                await outsource.create_task(dict(vendor_id=shared["id"], task_type="production"))
            await db.commit()
    finally:
        async with engine.begin() as conn:
            await conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
