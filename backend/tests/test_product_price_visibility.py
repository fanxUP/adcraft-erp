"""Regression tests for catalog price field visibility."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.permissions import PERM_CATALOG_VIEW_PRICE
from app.services.product_service import ProductService
from tests.test_product_service import (
    make_mock_material,
    make_mock_process,
    make_mock_product,
)


def make_viewer(*permission_codes: str):
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    role = SimpleNamespace(permissions=permissions)
    return SimpleNamespace(roles=[role])


@pytest.fixture
def catalog_service():
    repo = MagicMock()
    repo.list_products = AsyncMock(return_value=([], 0))
    repo.list_materials = AsyncMock(return_value=([], 0))
    repo.list_processes = AsyncMock(return_value=([], 0))
    db = AsyncMock()
    service = ProductService(db)
    service.repo = repo
    return service, repo


@pytest.mark.asyncio
async def test_catalog_lists_omit_price_fields_without_explicit_permission(catalog_service):
    service, mock_repo = catalog_service
    mock_repo.list_products.return_value = ([make_mock_product()], 1)
    mock_repo.list_materials.return_value = ([make_mock_material()], 1)
    mock_repo.list_processes.return_value = ([make_mock_process()], 1)
    service = ProductService(service.db, viewer=make_viewer())
    service.repo = mock_repo

    products, _ = await service.list_products(page=1, page_size=20)
    materials, _ = await service.list_materials(page=1, page_size=20)
    processes, _ = await service.list_processes(page=1, page_size=20)

    assert "default_price" not in products[0]
    assert "min_charge" not in products[0]
    assert "purchase_price" not in materials[0]
    assert "sale_price" not in materials[0]
    assert "default_price" not in processes[0]
    assert "startup_fee" not in processes[0]
    assert "min_charge" not in processes[0]


@pytest.mark.asyncio
async def test_catalog_lists_keep_price_fields_with_explicit_permission(catalog_service):
    service, mock_repo = catalog_service
    mock_repo.list_products.return_value = ([make_mock_product()], 1)
    mock_repo.list_materials.return_value = ([make_mock_material()], 1)
    mock_repo.list_processes.return_value = ([make_mock_process()], 1)
    service = ProductService(
        service.db,
        viewer=make_viewer(PERM_CATALOG_VIEW_PRICE),
    )
    service.repo = mock_repo

    products, _ = await service.list_products(page=1, page_size=20)
    materials, _ = await service.list_materials(page=1, page_size=20)
    processes, _ = await service.list_processes(page=1, page_size=20)

    assert products[0]["default_price"] == 100.0
    assert products[0]["min_charge"] == 50.0
    assert materials[0]["purchase_price"] == 50.0
    assert materials[0]["sale_price"] == 80.0
    assert processes[0]["default_price"] == 30.0
