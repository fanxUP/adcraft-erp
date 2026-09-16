"""统一供应商主数据的纯业务规则测试。"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.supplier_service import SupplierService, normalize_supplier_type


def test_supplier_type_is_normalized_and_validated():
    assert normalize_supplier_type("  material ") == "material"

    with pytest.raises(ValueError, match="供应商类型不受支持"):
        normalize_supplier_type("unknown")


def test_supplier_serialization_hides_bank_fields_by_default():
    supplier = SimpleNamespace(
        id="supplier-id",
        vendor_no="V260916-001",
        name="供应商甲",
        short_name="甲供应",
        supplier_type="material",
        contact_person="张三",
        phone="13800000000",
        email="supplier@example.com",
        address="乌鲁木齐",
        tax_id="91320000000000000A",
        bank_name="某银行",
        bank_account="6222000000000000",
        service_type=None,
        coop_rating=None,
        settlement_method="月结",
        settlement_days=30,
        tax_rate=None,
        remark=None,
        is_active=True,
        created_at=datetime(2026, 9, 16, 8, 0, 0),
    )

    payload = SupplierService.serialize_supplier(supplier)

    assert payload["name"] == "供应商甲"
    assert payload["supplier_type"] == "material"
    assert payload["bank_name"] is None
    assert payload["bank_account"] is None

    privileged = SupplierService.serialize_supplier(supplier, include_bank=True)
    assert privileged["bank_account"] == "6222000000000000"


def test_supplier_bank_write_requires_explicit_permission():
    service = SupplierService(None, viewer=SimpleNamespace(permissions=[]))

    with pytest.raises(ValueError, match="没有修改供应商收款账户的权限"):
        service._assert_bank_write_allowed({"bank_account": "6222"})

    privileged = SupplierService(
        None,
        viewer=SimpleNamespace(
            roles=[SimpleNamespace(permissions=[
                SimpleNamespace(code="supplier_center:read"),
                SimpleNamespace(code="supplier:read"),
                SimpleNamespace(code="supplier:bank:view"),
                SimpleNamespace(code="supplier:bank:edit"),
            ])],
        ),
    )
    privileged._assert_bank_write_allowed({"bank_account": "6222"})
