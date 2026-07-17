from datetime import date, datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contract_repo import ContractRepository
from app.services.number_generator import generate_contract_no


# 状态流转映射
CONTRACT_TRANSITIONS = {
    "draft": ["pending_sign"],
    "pending_sign": ["active", "draft"],
    "active": ["completed", "terminated"],
    "completed": [],
    "terminated": [],
}


class ContractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ContractRepository(db)

    def _to_response(self, contract) -> dict:
        return {
            "id": str(contract.id),
            "contract_no": contract.contract_no,
            "customer_name": contract.customer_name,
            "project_name": contract.project_name,
            "total_amount": float(contract.total_amount) if contract.total_amount else 0,
            "paid_amount": float(contract.paid_amount) if contract.paid_amount else 0,
            "unpaid_amount": float(contract.unpaid_amount) if contract.unpaid_amount else 0,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "sign_date": contract.sign_date.isoformat() if contract.sign_date else None,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
        }

    def _to_detail(self, contract) -> dict:
        base = self._to_response(contract)
        base.update({
            "customer_id": str(contract.customer_id),
            "our_signatory": contract.our_signatory,
            "customer_signatory": contract.customer_signatory,
            "content": contract.content,
            "remark": contract.remark,
            "created_by": str(contract.created_by) if contract.created_by else None,
            "orders": [
                {
                    "id": str(o.id),
                    "order_no": o.order_no,
                    "project_name": o.project_name,
                    "total_amount": float(o.total_amount) if o.total_amount else 0,
                }
                for o in (contract.orders or [])
            ],
            "quotes": [
                {
                    "id": str(q.id),
                    "quote_no": q.quote_no,
                    "project_name": q.project_name,
                    "total_amount": float(q.total_amount) if q.total_amount else 0,
                }
                for q in (contract.quotes or [])
            ],
        })
        return base

    async def list_contracts(
        self, page: int, page_size: int, status: str | None = None,
        keyword: str | None = None, customer_id: str | None = None,
    ) -> tuple[list, int]:
        skip = (page - 1) * page_size
        contracts, total = await self.repo.list_contracts(
            skip=skip, limit=page_size, status=status, keyword=keyword, customer_id=customer_id
        )
        return [self._to_response(c) for c in contracts], total

    async def get_contract(self, contract_id: UUID) -> dict | None:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            return None
        return self._to_detail(contract)

    async def create_contract(self, data: dict) -> dict:
        data["contract_no"] = await generate_contract_no(self.db)
        order_ids = data.get("order_ids", [])
        quote_ids = data.get("quote_ids", [])
        # Convert string UUIDs to actual UUIDs for the repo
        data["order_ids"] = [UUID(oid) for oid in (order_ids or [])]
        data["quote_ids"] = [UUID(qid) for qid in (quote_ids or [])]
        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        # Convert date strings to date objects
        for field in ("sign_date", "start_date", "end_date"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = date.fromisoformat(val)
                except ValueError:
                    data[field] = datetime.fromisoformat(val).date()

        contract = await self.repo.create(data)
        # Re-fetch to load secondary relationships (orders/quotes)
        contract = await self.repo.get_by_id(contract.id)
        return self._to_detail(contract)

    async def update_contract(self, contract_id: UUID, data: dict) -> dict:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")

        # Convert string UUIDs
        if data.get("order_ids") is not None:
            data["order_ids"] = [UUID(oid) for oid in data["order_ids"]]
        if data.get("quote_ids") is not None:
            data["quote_ids"] = [UUID(qid) for qid in data["quote_ids"]]
        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        # Convert date strings to date objects
        for field in ("sign_date", "start_date", "end_date"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = date.fromisoformat(val)
                except ValueError:
                    data[field] = datetime.fromisoformat(val).date()

        contract = await self.repo.update(contract, data)
        # Re-fetch to load secondary relationships after updates
        contract = await self.repo.get_by_id(contract.id)
        return self._to_detail(contract)

    async def delete_contract(self, contract_id: UUID) -> bool:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            return False
        await self.repo.soft_delete(contract)
        return True

    async def change_status(self, contract_id: UUID, to_status: str, reason: str | None = None) -> dict:
        contract = await self.repo.get_by_id(contract_id)
        if not contract:
            raise ValueError("合同不存在")

        allowed = CONTRACT_TRANSITIONS.get(contract.status, [])
        if to_status not in allowed:
            raise ValueError(f"合同状态不允许从「{contract.status}」变更为「{to_status}」")

        contract.status = to_status
        await self.db.flush()
        # Re-fetch to load secondary relationships
        contract = await self.repo.get_by_id(contract.id)
        return self._to_detail(contract)
