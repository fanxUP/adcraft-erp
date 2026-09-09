"""Shared backend presentation semantics for task and outsource contracts.

These helpers deliberately describe object state for the UI.  They do not
grant permissions; route dependencies and service validation remain the final
authorization and business-rule boundaries.
"""

from app.schemas.common import ActionCapability, StatusView, UiTone


_TONE_BY_STATUS: dict[str, UiTone] = {
    "completed": "success",
    "complete": "success",
    "confirmed": "success",
    "cancelled": "neutral",
    "canceled": "neutral",
    "blocked": "danger",
    "rework": "warning",
    "pending": "warning",
    "pending_confirm": "warning",
    "pending_review": "warning",
    "pending_acceptance": "warning",
    "assigned": "info",
    "designing": "info",
    "in_design": "info",
    "in_production": "info",
    "production": "info",
    "in_installation": "info",
    "installation": "info",
    "in_progress": "info",
    "settled": "success",
}

_TERMINAL_STATUSES = {"completed", "complete", "confirmed", "cancelled", "canceled", "settled"}

_OUTSOURCE_LABELS = {
    "pending": "待处理",
    "in_progress": "进行中",
    "completed": "已完成",
    "settled": "已结算",
    "cancelled": "已取消",
}

_ORDER_LABELS = {
    "draft": "草稿",
    "pending_confirm": "待确认",
    "confirmed": "已确认",
    "designing": "设计中",
    "in_production": "制作中",
    "in_installation": "安装中",
    "completed": "已完成",
    "cancelled": "已取消",
}

_ORDER_TONES: dict[str, UiTone] = {
    "draft": "neutral",
    "pending_confirm": "warning",
    "confirmed": "info",
    "designing": "info",
    "in_production": "info",
    "in_installation": "info",
    "completed": "success",
    "cancelled": "neutral",
}

_QUOTE_LABELS = {
    "draft": "草稿",
    "confirmed": "已确认",
    "converted": "已转订单",
    "cancelled": "已作废",
}

_QUOTE_TONES: dict[str, UiTone] = {
    "draft": "neutral",
    "confirmed": "success",
    "converted": "info",
    "cancelled": "neutral",
}

_CONTRACT_LABELS = {
    "draft": "草稿",
    "active": "生效中",
    "completed": "已完成",
    "cancelled": "已取消",
    "terminated": "已终止",
}

_CONTRACT_TONES: dict[str, UiTone] = {
    "draft": "neutral",
    "active": "info",
    "completed": "success",
    "cancelled": "neutral",
    "terminated": "danger",
}

_STATEMENT_LABELS = {
    "draft": "草稿",
    "confirmed": "已确认",
    "cancelled": "已作废",
}


def make_status_view(
    code: str | None,
    label: str | None = None,
    *,
    tone: UiTone | None = None,
    terminal: bool | None = None,
) -> StatusView:
    normalized = (code or "unknown").strip() or "unknown"
    return StatusView(
        code=normalized,
        label=(label or normalized).strip() or normalized,
        tone=tone or _TONE_BY_STATUS.get(normalized, "neutral"),
        terminal=normalized in _TERMINAL_STATUSES if terminal is None else terminal,
    )


def make_action_capability(
    allowed: bool,
    disabled_reason: str | None = None,
    *,
    requires_confirmation: bool = False,
) -> ActionCapability:
    return ActionCapability(
        allowed=allowed,
        disabled_reason=disabled_reason if not allowed else None,
        requires_confirmation=requires_confirmation,
    )


def make_outsource_status_view(status: str | None) -> StatusView:
    normalized = (status or "unknown").strip() or "unknown"
    return make_status_view(normalized, _OUTSOURCE_LABELS.get(normalized))


def make_order_status_view(status: str | None) -> StatusView:
    """Return the stable status semantics shared by order list and detail views."""
    normalized = (status or "unknown").strip() or "unknown"
    return make_status_view(
        normalized,
        _ORDER_LABELS.get(normalized),
        tone=_ORDER_TONES.get(normalized),
    )


def make_quote_status_view(status: str | None) -> StatusView:
    """Return quote-specific labels without changing the quote workflow."""
    normalized = (status or "unknown").strip() or "unknown"
    return make_status_view(
        normalized,
        _QUOTE_LABELS.get(normalized),
        tone=_QUOTE_TONES.get(normalized),
        terminal=normalized in {"converted", "cancelled"},
    )


def make_contract_status_view(status: str | None) -> StatusView:
    """Return contract lifecycle semantics used by sales and finance pages."""
    normalized = (status or "unknown").strip() or "unknown"
    return make_status_view(
        normalized,
        _CONTRACT_LABELS.get(normalized),
        tone=_CONTRACT_TONES.get(normalized),
        terminal=normalized in {"completed", "cancelled", "terminated"},
    )


def make_statement_status_view(status: str | None) -> StatusView:
    normalized = (status or "unknown").strip() or "unknown"
    return make_status_view(
        normalized,
        _STATEMENT_LABELS.get(normalized),
        tone="success" if normalized == "confirmed" else "neutral" if normalized in {"draft", "cancelled"} else None,
        terminal=normalized in {"confirmed", "cancelled"},
    )


def make_payment_status_view(is_voided: bool) -> StatusView:
    return make_status_view(
        "voided" if is_voided else "active",
        "已作废" if is_voided else "有效",
        tone="danger" if is_voided else "success",
        terminal=is_voided,
    )
