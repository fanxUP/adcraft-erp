"""Validation for new payment facts; legacy nullable records remain readable."""
from datetime import UTC, date, datetime


def require_payment_date(value) -> datetime:
    if value is None or not isinstance(value, (str, date)):
        raise ValueError("请选择实际付款日期")
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime.combine(value, datetime.min.time())
        else:
            raw = value.strip()
            if not raw:
                raise ValueError()
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("付款日期无效，请选择实际付款日期") from exc
    return parsed.astimezone(UTC).replace(tzinfo=None) if parsed.tzinfo else parsed
