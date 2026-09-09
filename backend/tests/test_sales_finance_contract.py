from app.domain.presentation import (
    make_contract_status_view,
    make_payment_status_view,
    make_quote_status_view,
    make_statement_status_view,
)
from app.schemas.contract import ContractListResponse
from app.schemas.payment import DebtResponse, PaymentResponse, StatementResponse
from app.schemas.quote import QuoteDetailResponse, QuoteListResponse


def test_sales_status_views_have_stable_labels_and_terminal_semantics():
    assert make_quote_status_view("converted").model_dump() == {
        "code": "converted",
        "label": "已转订单",
        "tone": "info",
        "terminal": True,
    }
    assert make_contract_status_view("active").label == "生效中"
    assert make_contract_status_view("completed").terminal is True


def test_finance_status_views_cover_payment_statement_and_settlement():
    assert make_payment_status_view(False).label == "有效"
    assert make_payment_status_view(True).terminal is True
    assert make_statement_status_view("confirmed").tone == "success"


def test_sales_finance_response_schemas_accept_canonical_fields():
    assert "status_view" in QuoteListResponse.model_fields
    assert "status_view" in QuoteDetailResponse.model_fields
    assert "status_view" in ContractListResponse.model_fields
    assert "status_view" in PaymentResponse.model_fields
    assert "capabilities" in StatementResponse.model_fields
    assert "capabilities" in DebtResponse.model_fields
