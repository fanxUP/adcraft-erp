"""订单回退报价能力已下线后的兼容性回归测试。"""


def test_order_to_quote_route_is_not_registered():
    import app.main as main

    assert not any("convert-to-quote" in path for path in main.app.openapi()["paths"])


def test_order_to_quote_service_method_is_not_public():
    from app.services.business_document_service import BusinessDocumentService

    assert not hasattr(BusinessDocumentService, "convert_order_to_quote")
