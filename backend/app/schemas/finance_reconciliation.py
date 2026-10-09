from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


EvidenceType = Literal["bank_statement", "payment_voucher", "other"]
ReconciliationSource = Literal["expense", "project_cost", "outsource_task", "outsource_payment"]
OverlapDecision = Literal[
    "confirmed_duplicate",
    "confirmed_not_duplicate",
    "needs_evidence",
]


class PaymentDateReconciliationCreate(BaseModel):
    source_type: ReconciliationSource
    source_id: UUID
    amount: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    paid_at: date
    evidence_type: EvidenceType
    evidence_reference: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class PaymentDateReconciliationVoid(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class CostOverlapReviewWrite(BaseModel):
    cost_id: UUID
    task_id: UUID
    decision: OverlapDecision
    evidence_type: EvidenceType | None = None
    evidence_reference: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)
