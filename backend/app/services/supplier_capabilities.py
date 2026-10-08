"""Shared supplier identities and external-service capabilities."""

SUPPLIER_TYPE_LABELS = {
    "outsource": "外协服务", "material": "材料供应", "equipment": "设备供应",
    "transport": "运输服务", "service": "其他服务", "other": "其他供应商",
}
SERVICE_TYPE_LABELS = {
    "production": "制作", "installation": "安装", "design": "设计", "transport": "运输",
}


def normalize_choices(values, options, label, *, required=False):
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise ValueError(f"{label}必须为选项列表")
    normalized = list(dict.fromkeys(v.strip().lower() for v in values))
    if required and not normalized:
        raise ValueError(f"请至少选择一项{label}")
    if any(v not in options for v in normalized):
        raise ValueError(f"{label}不受支持")
    return normalized


def supplier_roles(supplier):
    values = getattr(supplier, "supplier_types", None)
    if isinstance(values, list):
        return values
    legacy = getattr(supplier, "supplier_type", None)
    return [legacy if isinstance(legacy, str) else "outsource"]


def supplier_services(supplier):
    values = getattr(supplier, "service_types", None)
    if isinstance(values, list):
        return values
    legacy = getattr(supplier, "service_type", None)
    if "outsource" not in supplier_roles(supplier):
        return []
    return [legacy] if isinstance(legacy, str) and legacy in SERVICE_TYPE_LABELS else list(SERVICE_TYPE_LABELS)
