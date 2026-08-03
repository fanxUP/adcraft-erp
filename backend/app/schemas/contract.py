from pydantic import BaseModel
from app.schemas.common import CoercedModel
from datetime import datetime


class ContractCreate(BaseModel):
    customer_id: str
    customer_name: str
    project_name: str
    total_amount: float = 0
    paid_amount: float = 0
    unpaid_amount: float = 0
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    our_signatory: str | None = None
    customer_signatory: str | None = None
    contract_type: str | None = None
    content: str | None = None
    remark: str | None = None
    order_ids: list[str] = []


class ContractUpdate(BaseModel):
    customer_id: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    total_amount: float | None = None
    paid_amount: float | None = None
    unpaid_amount: float | None = None
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    our_signatory: str | None = None
    customer_signatory: str | None = None
    contract_type: str | None = None
    content: str | None = None
    remark: str | None = None


class ContractListResponse(CoercedModel):
    id: str
    contract_no: str
    customer_name: str
    project_name: str
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    contract_type: str | None = None
    status: str
    sign_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class SimpleOrderRef(CoercedModel):
    id: str
    order_no: str
    project_name: str
    total_amount: float

    model_config = {"from_attributes": True}



class ContractDetailResponse(ContractListResponse):
    customer_id: str
    our_signatory: str | None = None
    customer_signatory: str | None = None
    attachment_path: str | None = None
    attachment_name: str | None = None
    content: str | None = None
    remark: str | None = None
    created_by: str | None = None
    orders: list[SimpleOrderRef] = []

    model_config = {"from_attributes": True}


class ContractStatusChange(BaseModel):
    to_status: str
    reason: str | None = None


class ContractLinkOrders(BaseModel):
    """把订单追加关联到已有合同（纯追加，不影响合同已有单据关联）。"""
    order_ids: list[str] = []
