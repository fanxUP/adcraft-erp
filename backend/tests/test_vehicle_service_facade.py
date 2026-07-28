"""车辆服务拆分后的兼容接口测试。"""

from app.services.vehicle_compliance_service import VehicleComplianceService
from app.services.vehicle_dispatch_service import VehicleDispatchService
from app.services.vehicle_finance_service import VehicleFinanceService
from app.services.vehicle_registry_service import VehicleRegistryService
from app.services.vehicle_service import VehicleService


def test_vehicle_service_preserves_all_domain_interfaces():
    assert issubclass(VehicleService, VehicleRegistryService)
    assert issubclass(VehicleService, VehicleDispatchService)
    assert issubclass(VehicleService, VehicleFinanceService)
    assert issubclass(VehicleService, VehicleComplianceService)

    expected_methods = {
        "list_vehicles",
        "list_drivers",
        "list_requests",
        "list_dispatches",
        "list_trip_records",
        "list_fuel_records",
        "list_maintenance_records",
        "list_cost_allocations",
        "list_certificates",
        "list_incidents",
    }
    assert expected_methods.issubset(set(dir(VehicleService)))
