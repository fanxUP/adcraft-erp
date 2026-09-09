from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.ai.ai_enhanced.llm_quote_assistant import LLMQuoteAssistant


class _RowResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _SingleReadScalarResult:
    def __init__(self, rows):
        self._rows = rows
        self.read_count = 0

    def scalars(self):
        return self

    def all(self):
        self.read_count += 1
        return self._rows if self.read_count == 1 else []


class _FakeDB:
    def __init__(self, result):
        self.result = result

    async def execute(self, *_args, **_kwargs):
        return self.result


@pytest.mark.asyncio
async def test_pricing_history_query_result_matches_rendering_contract():
    db = _FakeDB(_RowResult([
        (
            "亚克力字",
            2,
            Decimal("100"),
            Decimal("98"),
            Decimal("90"),
            Decimal("110"),
            Decimal("12"),
            Decimal("20"),
        ),
    ]))

    result = await LLMQuoteAssistant(db, ai_client=None)._build_pricing_history()

    assert "亚克力字" in result
    assert "平均设计费: ¥12" in result
    assert "平均安装费: ¥20" in result


@pytest.mark.asyncio
async def test_customer_context_keeps_price_agreements_after_one_result_read():
    agreement = SimpleNamespace(
        product_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        pricing_method="fixed",
        price_value=Decimal("100"),
        discount_rate=Decimal("1"),
    )
    scalar_result = _SingleReadScalarResult([agreement])
    db = _FakeDB(scalar_result)

    result = await LLMQuoteAssistant(db, ai_client=None)._build_customer_context(
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    )

    assert result is not None
    assert str(agreement.product_id) in result
    assert scalar_result.read_count == 1
