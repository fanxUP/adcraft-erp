"""Regression tests for structured price redaction in chat payloads."""

from types import SimpleNamespace

from app.api.conversations import _redact_chat_payload
from app.core.permissions import PERM_ORDER_READ


def make_viewer(*permission_codes: str):
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    role = SimpleNamespace(permissions=permissions)
    return SimpleNamespace(roles=[role])


def test_chat_payload_omits_order_and_line_prices_for_execution_users():
    payload = {
        "title": "订单 #O20260910-0001",
        "amount": 12800,
        "total_amount": 12800,
        "safe": {"quantity": 3, "width": 1200},
        "items": [{"item_name": "标识牌", "unit_price": 200, "subtotal_amount": 600}],
    }

    result = _redact_chat_payload(payload, make_viewer())

    assert result["title"] == payload["title"]
    assert result["safe"] == payload["safe"]
    assert "amount" not in result
    assert "total_amount" not in result
    assert "unit_price" not in result["items"][0]
    assert "subtotal_amount" not in result["items"][0]
    # Redaction must not mutate the message stored in the session.
    assert payload["amount"] == 12800


def test_chat_payload_keeps_prices_only_for_users_with_explicit_permissions():
    payload = {
        "amount": 12800,
        "total_amount": 12800,
        "items": [{"unit_price": 200, "subtotal_amount": 600}],
    }

    result = _redact_chat_payload(
        payload,
        make_viewer(PERM_ORDER_READ, "order:view_price", "order_item:view_price"),
    )

    assert result == payload
