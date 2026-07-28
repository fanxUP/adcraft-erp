"""CDR 报价服务拆分后的兼容接口测试。"""

from app.services.cdr_quote_conversion_service import CdrQuoteConversionService
from app.services.cdr_quote_governance_service import CdrQuoteGovernanceService
from app.services.cdr_quote_integration_service import CdrQuoteIntegrationService
from app.services.cdr_quote_pricing_service import CdrQuotePricingService
from app.services.cdr_quote_service import CdrQuoteService


def test_cdr_quote_service_preserves_domain_interfaces():
    assert issubclass(CdrQuoteService, CdrQuotePricingService)
    assert issubclass(CdrQuoteService, CdrQuoteGovernanceService)
    assert issubclass(CdrQuoteService, CdrQuoteConversionService)
    assert issubclass(CdrQuoteService, CdrQuoteIntegrationService)

    expected_methods = {
        "calculate",
        "create_quote_version",
        "request_approval",
        "create_rule_set",
        "convert_to_order",
        "save_quote_geometry",
        "register_device",
        "create_capture",
        "create_quote_from_capture",
    }
    assert expected_methods.issubset(set(dir(CdrQuoteService)))
