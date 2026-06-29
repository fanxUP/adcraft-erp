"""Tests for number generation: quote/order/customer/task number generation.

Numbers follow the format: {PREFIX}{YYYYMMDD}-{SEQ:04d}
Example: I20260629-0001, Q20260629-0042
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.number_generator import (
    generate_design_no,
    generate_installation_no,
    generate_production_no,
    generate_quote_no,
    generate_order_no,
    generate_customer_no,
    generate_payment_no,
)
from tests.conftest import MockResult


@pytest.fixture
def mock_db():
    """Create a mock DB session with configurable execute return."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_first_number_generated(mock_db):
    """When no existing records, the sequence starts at 0001."""
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_installation_no(mock_db)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert no == f"I{today}-0001"


@pytest.mark.asyncio
async def test_second_number_generated(mock_db):
    """When one record exists, the next sequence is 0002."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=f"I{today}-0001")
    no = await generate_installation_no(mock_db)
    assert no == f"I{today}-0002"


@pytest.mark.asyncio
async def test_sequence_mid_range(mock_db):
    """Sequence continues from existing highest number."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=f"I{today}-0042")
    no = await generate_installation_no(mock_db)
    assert no == f"I{today}-0043"


@pytest.mark.asyncio
async def test_design_number_generation(mock_db):
    """Design task numbers use the D prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_design_no(mock_db)
    assert no == f"D{today}-0001"


@pytest.mark.asyncio
async def test_production_number_generation(mock_db):
    """Production task numbers use the P prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_production_no(mock_db)
    assert no == f"P{today}-0001"


@pytest.mark.asyncio
async def test_quote_number_generation(mock_db):
    """Quote numbers use the Q prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_quote_no(mock_db)
    assert no == f"Q{today}-0001"


@pytest.mark.asyncio
async def test_order_number_generation(mock_db):
    """Order numbers use the O prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_order_no(mock_db)
    assert no == f"O{today}-0001"


@pytest.mark.asyncio
async def test_customer_number_generation(mock_db):
    """Customer numbers use the C prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_customer_no(mock_db)
    assert no == f"C{today}-0001"


@pytest.mark.asyncio
async def test_payment_number_generation(mock_db):
    """Payment numbers use the PAY prefix."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_payment_no(mock_db)
    assert no.startswith(f"PAY{today}")
    assert no.endswith("-0001")


@pytest.mark.asyncio
async def test_number_has_correct_format(mock_db):
    """Generated number matches the expected format pattern."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_installation_no(mock_db)
    parts = no.split("-")
    assert len(parts) == 2
    assert parts[0] == f"I{today}"
    assert len(parts[1]) == 4
    assert parts[1].isdigit()


@pytest.mark.asyncio
async def test_uses_correct_date(mock_db):
    """The generated number uses the current UTC date."""
    mock_db.execute.return_value = MockResult(scalar_return=None)
    no = await generate_installation_no(mock_db)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert today in no
    assert no.startswith(f"I{today}")
