from pydantic import BaseModel


class FrameworkContractProjectCreate(BaseModel):
    contract_id: str
    customer_id: str
    customer_name: str
    project_name: str
    project_amount: float = 0
    department: str | None = None
    remark: str | None = None
    order_ids: list[str] = []
    quote_ids: list[str] = []


class FrameworkContractProjectUpdate(BaseModel):
    project_name: str | None = None
    project_amount: float | None = None
    department: str | None = None
    remark: str | None = None
    order_ids: list[str] | None = None
    quote_ids: list[str] | None = None


class FrameworkContractProjectResponse(BaseModel):
    id: str
    contract_id: str
    customer_id: str
    customer_name: str
    department: str | None = None
    project_name: str
    project_amount: float
    remark: str | None = None
    attachment_path: str | None = None
    attachment_name: str | None = None
    created_at: str | None = None
    model_config = {"from_attributes": True}


class FrameworkContractProjectDetailResponse(FrameworkContractProjectResponse):
    orders: list["SimpleOrderRef"] = []
    quotes: list["SimpleQuoteRef"] = []
    model_config = {"from_attributes": True}


from app.schemas.contract import SimpleOrderRef, SimpleQuoteRef
