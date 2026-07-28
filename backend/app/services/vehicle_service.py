"""车辆领域兼容外观。

API 层继续依赖 VehicleService；具体职责按领域拆分到四个服务中。
"""

from app.services.vehicle_compliance_service import VehicleComplianceService
from app.services.vehicle_dispatch_service import VehicleDispatchService
from app.services.vehicle_finance_service import VehicleFinanceService
from app.services.vehicle_registry_service import VehicleRegistryService


class VehicleService(
    VehicleRegistryService,
    VehicleDispatchService,
    VehicleFinanceService,
    VehicleComplianceService,
):
    pass
