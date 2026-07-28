"""Public workflow guidance dispatcher."""

from .common import unknown_guidance
from .documents import (
    build_acceptance_guidance,
    build_order_guidance,
    build_quote_guidance,
)
from .tasks import build_task_guidance


def build_workflow_guidance(snapshot: dict) -> dict:
    """Build safe, read-only guidance from a normalized business snapshot."""
    business_type = str(snapshot.get("business_type") or "")
    if business_type == "order":
        return build_order_guidance(snapshot)
    if business_type == "quote":
        return build_quote_guidance(snapshot)
    if business_type in ("design_task", "production_task", "installation_task"):
        return build_task_guidance(snapshot, business_type)
    if business_type == "acceptance":
        return build_acceptance_guidance(snapshot)
    return unknown_guidance(snapshot, "/")
