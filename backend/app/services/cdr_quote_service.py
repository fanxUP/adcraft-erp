"""CDR 智能报价兼容外观。"""

from uuid import UUID

from app.services.cdr_quote_conversion_service import CdrQuoteConversionService
from app.services.cdr_quote_governance_service import CdrQuoteGovernanceService
from app.services.cdr_quote_integration_service import CdrQuoteIntegrationService
from app.services.cdr_quote_pricing_service import CdrQuotePricingService


class CdrQuoteService(
    CdrQuotePricingService,
    CdrQuoteGovernanceService,
    CdrQuoteConversionService,
    CdrQuoteIntegrationService,
):
    """聚合报价、审批、转单和外部集成四个子领域。"""

    pass
