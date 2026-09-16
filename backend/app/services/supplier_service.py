"""Unified supplier master-data service.

The service deliberately uses the historical ``outsource_vendors`` table as
the single supplier source.  External-work screens can keep calling their
legacy service, while finance and payable screens use this service to resolve
one stable supplier ID.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    PERM_SUPPLIER_BANK_READ,
    PERM_SUPPLIER_BANK_UPDATE,
    PERM_SUPPLIER_LEDGER_READ,
    user_has_permission,
)
from app.models.outsource import OutsourceTask, OutsourceVendor
from app.models.payment import Expense
from app.models.project_cost import ProjectCost
from app.models.user import User
from app.services.number_generator import generate_vendor_no
from app.services.payable_service import PayableService


SUPPLIER_TYPE_LABELS = {
    "outsource": "外协服务",
    "material": "材料供应商",
    "equipment": "设备供应商",
    "transport": "运输服务",
    "service": "其他服务",
    "other": "其他供应商",
}


def normalize_supplier_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in SUPPLIER_TYPE_LABELS:
        raise ValueError("供应商类型不受支持")
    return normalized


def _decimal_or_zero(value) -> Decimal:
    return Decimal(str(value or 0))


def _summarize_ledger_sources(
    source_type: str,
    sources: list[object],
    payment_summaries: dict[tuple[str, UUID], tuple[Decimal, int]],
) -> dict[str, Decimal | int]:
    """Aggregate source totals with the same ledger rules as 应付管理."""

    total_amount = Decimal("0")
    payable_total = Decimal("0")
    payable_paid = Decimal("0")
    source_count = 0

    payable_field = "debt_amount" if source_type == "project_cost" else "payable_amount"
    for source in sources:
        source_count += 1
        source_total = _decimal_or_zero(getattr(source, "amount", 0))
        source_payable = max(
            Decimal("0"),
            min(_decimal_or_zero(getattr(source, payable_field, 0)), source_total),
        )
        paid, payment_count = payment_summaries.get(
            (source_type, source.id), (Decimal("0"), 0)
        )
        paid = _decimal_or_zero(paid)
        if (
            source_type == "project_cost"
            and bool(getattr(source, "is_settled", False))
            and payment_count == 0
        ):
            paid = source_payable
        payable_paid += max(Decimal("0"), min(paid, source_payable))
        total_amount += source_total
        payable_total += source_payable

    remaining = max(Decimal("0"), payable_total - payable_paid)
    initial_paid = max(Decimal("0"), total_amount - payable_total)
    return {
        "count": source_count,
        "amount": total_amount,
        "payable": payable_total,
        "initial_paid": initial_paid,
        "paid": initial_paid + payable_paid,
        "remaining": remaining,
    }


class SupplierService:
    def __init__(self, db: AsyncSession, viewer: User | None = None):
        self.db = db
        self.viewer = viewer

    @staticmethod
    def serialize_supplier(
        supplier: OutsourceVendor,
        *,
        include_bank: bool = False,
        stats: dict | None = None,
    ) -> dict:
        supplier_type = getattr(supplier, "supplier_type", None) or "outsource"
        tax_rate = getattr(supplier, "tax_rate", None)
        payload = {
            "id": str(supplier.id),
            "vendor_no": supplier.vendor_no,
            "name": supplier.name,
            "short_name": getattr(supplier, "short_name", None),
            "supplier_type": supplier_type,
            "supplier_type_label": SUPPLIER_TYPE_LABELS.get(supplier_type, supplier_type),
            "contact_person": supplier.contact_person,
            "phone": supplier.phone,
            "email": getattr(supplier, "email", None),
            "address": supplier.address,
            "tax_id": getattr(supplier, "tax_id", None),
            "bank_name": getattr(supplier, "bank_name", None) if include_bank else None,
            "bank_account": getattr(supplier, "bank_account", None) if include_bank else None,
            "tax_rate": float(tax_rate) if tax_rate is not None else None,
            "settlement_method": getattr(supplier, "settlement_method", None),
            "settlement_days": getattr(supplier, "settlement_days", None),
            "service_type": supplier.service_type,
            "coop_rating": supplier.coop_rating,
            "remark": supplier.remark,
            "is_active": bool(supplier.is_active),
            "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
            "stats": stats,
        }
        return payload

    def _include_bank(self) -> bool:
        return self.viewer is None or user_has_permission(self.viewer, PERM_SUPPLIER_BANK_READ)

    def _include_ledger(self) -> bool:
        return self.viewer is None or user_has_permission(self.viewer, PERM_SUPPLIER_LEDGER_READ)

    def _can_update_bank(self) -> bool:
        return self.viewer is None or user_has_permission(self.viewer, PERM_SUPPLIER_BANK_UPDATE)

    def _assert_bank_write_allowed(self, data: dict) -> None:
        if self._can_update_bank():
            return
        if any(key in data for key in ("bank_name", "bank_account")):
            raise ValueError("当前角色没有修改供应商收款账户的权限")

    async def list_suppliers(
        self,
        page: int,
        page_size: int,
        *,
        keyword: str | None = None,
        supplier_type: str | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[dict], int]:
        query = select(OutsourceVendor).where(OutsourceVendor.deleted_at.is_(None))
        if keyword and keyword.strip():
            fuzzy = f"%{keyword.strip()}%"
            query = query.where(
                or_(
                    OutsourceVendor.name.ilike(fuzzy),
                    OutsourceVendor.short_name.ilike(fuzzy),
                    OutsourceVendor.tax_id.ilike(fuzzy),
                    OutsourceVendor.contact_person.ilike(fuzzy),
                )
            )
        if supplier_type:
            query = query.where(OutsourceVendor.supplier_type == normalize_supplier_type(supplier_type))
        if is_active is not None:
            query = query.where(OutsourceVendor.is_active.is_(is_active))

        count = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = int(count.scalar() or 0)
        result = await self.db.execute(
            query.order_by(OutsourceVendor.is_active.desc(), OutsourceVendor.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [
            self.serialize_supplier(v, include_bank=self._include_bank())
            for v in result.scalars().all()
        ], total

    async def _get_active_record(self, supplier_id: UUID, *, include_inactive: bool = False):
        query = select(OutsourceVendor).where(
            OutsourceVendor.id == supplier_id,
            OutsourceVendor.deleted_at.is_(None),
        )
        if not include_inactive:
            query = query.where(OutsourceVendor.is_active.is_(True))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _stats(self, supplier_id: UUID) -> dict:
        cost_result = await self.db.execute(
            select(ProjectCost).where(
                ProjectCost.supplier_id == supplier_id,
                ProjectCost.deleted_at.is_(None),
            )
        )
        cost_sources = list(cost_result.scalars().all())

        expense_result = await self.db.execute(
            select(Expense).where(
                Expense.supplier_id == supplier_id,
                Expense.deleted_at.is_(None),
            )
        )
        expense_sources = list(expense_result.scalars().all())

        source_pairs = [
            ("project_cost", source.id) for source in cost_sources
        ] + [
            ("expense", source.id) for source in expense_sources
        ]
        payment_summaries = await PayableService(self.db).get_payment_summaries(source_pairs)
        cost_stats = _summarize_ledger_sources(
            "project_cost", cost_sources, payment_summaries
        )
        expense_stats = _summarize_ledger_sources(
            "expense", expense_sources, payment_summaries
        )

        task_result = await self.db.execute(
            select(
                func.count(OutsourceTask.id),
                func.coalesce(func.sum(OutsourceTask.total_amount), 0),
                func.coalesce(func.sum(OutsourceTask.unpaid_amount), 0),
            ).where(
                OutsourceTask.vendor_id == supplier_id,
                OutsourceTask.deleted_at.is_(None),
            )
        )
        task_count, task_amount, task_unpaid = task_result.one()
        return {
            "project_cost_count": int(cost_stats["count"]),
            "project_cost_amount": float(cost_stats["amount"]),
            "project_cost_payable": float(cost_stats["payable"]),
            "project_cost_paid": float(cost_stats["paid"]),
            "project_cost_remaining": float(cost_stats["remaining"]),
            "expense_count": int(expense_stats["count"]),
            "expense_amount": float(expense_stats["amount"]),
            "expense_payable": float(expense_stats["payable"]),
            "expense_paid": float(expense_stats["paid"]),
            "expense_remaining": float(expense_stats["remaining"]),
            "outsource_task_count": int(task_count or 0),
            "outsource_task_amount": float(_decimal_or_zero(task_amount)),
            "outsource_task_unpaid": float(_decimal_or_zero(task_unpaid)),
        }

    async def get_supplier(self, supplier_id: UUID) -> dict | None:
        supplier = await self._get_active_record(supplier_id, include_inactive=True)
        if not supplier:
            return None
        stats = await self._stats(supplier.id) if self._include_ledger() else None
        return self.serialize_supplier(
            supplier,
            include_bank=self._include_bank(),
            stats=stats,
        )

    async def _assert_unique_name(self, name: str, exclude_id: UUID | None = None) -> None:
        normalized = name.strip()
        query = select(OutsourceVendor.id).where(
            OutsourceVendor.deleted_at.is_(None),
            func.lower(func.trim(OutsourceVendor.name)) == normalized.lower(),
        )
        if exclude_id:
            query = query.where(OutsourceVendor.id != exclude_id)
        result = await self.db.execute(query.limit(1))
        if result.scalar_one_or_none() is not None:
            raise ValueError("供应商名称已存在，请直接使用已有供应商")

    @staticmethod
    def _clean_payload(data: dict) -> dict:
        cleaned = dict(data)
        for key, value in list(cleaned.items()):
            if isinstance(value, str):
                cleaned[key] = value.strip() or None
        if "name" in cleaned:
            cleaned["name"] = str(cleaned["name"] or "").strip()
        if "supplier_type" in cleaned and cleaned["supplier_type"] is not None:
            cleaned["supplier_type"] = normalize_supplier_type(cleaned["supplier_type"])
        return cleaned

    async def create_supplier(self, data: dict) -> dict:
        cleaned = self._clean_payload(data)
        self._assert_bank_write_allowed(cleaned)
        name = cleaned.get("name") or ""
        if not name:
            raise ValueError("供应商名称不能为空")
        await self._assert_unique_name(name)
        cleaned["supplier_type"] = normalize_supplier_type(cleaned.get("supplier_type") or "other")
        cleaned["vendor_no"] = await generate_vendor_no(self.db)
        supplier = OutsourceVendor(**cleaned)
        self.db.add(supplier)
        await self.db.flush()
        return self.serialize_supplier(supplier, include_bank=self._include_bank())

    async def update_supplier(self, supplier_id: UUID, data: dict) -> dict:
        supplier = await self._get_active_record(supplier_id, include_inactive=True)
        if not supplier:
            raise ValueError("供应商不存在")
        cleaned = self._clean_payload(data)
        self._assert_bank_write_allowed(cleaned)
        if "name" in cleaned:
            if not cleaned["name"]:
                raise ValueError("供应商名称不能为空")
            await self._assert_unique_name(cleaned["name"], exclude_id=supplier.id)
        if "supplier_type" in cleaned:
            cleaned["supplier_type"] = normalize_supplier_type(cleaned["supplier_type"])
        allowed = {
            "name", "short_name", "supplier_type", "contact_person", "phone", "email",
            "address", "tax_id", "bank_name", "bank_account", "tax_rate",
            "settlement_method", "settlement_days", "service_type", "coop_rating",
            "remark", "is_active",
        }
        for key, value in cleaned.items():
            if key in allowed:
                setattr(supplier, key, value)
        await self.db.flush()
        stats = await self._stats(supplier.id) if self._include_ledger() else None
        return self.serialize_supplier(
            supplier,
            include_bank=self._include_bank(),
            stats=stats,
        )

    async def deactivate_supplier(self, supplier_id: UUID) -> dict:
        supplier = await self._get_active_record(supplier_id, include_inactive=True)
        if not supplier:
            raise ValueError("供应商不存在")
        supplier.is_active = False
        await self.db.flush()
        return self.serialize_supplier(supplier, include_bank=self._include_bank())

    async def resolve_active_supplier(self, supplier_id: str | UUID | None) -> OutsourceVendor | None:
        if supplier_id is None or supplier_id == "":
            return None
        try:
            normalized_id = supplier_id if isinstance(supplier_id, UUID) else UUID(str(supplier_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("供应商ID格式不正确") from exc
        supplier = await self._get_active_record(normalized_id)
        if not supplier:
            raise ValueError("供应商不存在或已停用")
        return supplier

    async def find_unique_active_supplier(self, name: str | None) -> OutsourceVendor | None:
        normalized = (name or "").strip()
        if not normalized:
            return None
        result = await self.db.execute(
            select(OutsourceVendor).where(
                OutsourceVendor.deleted_at.is_(None),
                OutsourceVendor.is_active.is_(True),
                func.lower(func.trim(OutsourceVendor.name)) == normalized.lower(),
            ).limit(2)
        )
        rows = list(result.scalars().all())
        return rows[0] if len(rows) == 1 else None
