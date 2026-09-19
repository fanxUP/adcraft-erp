from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.domain.presentation import make_action_capability, make_status_view
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.project_cost import ProjectCost, ProjectCostItemLink
from app.models.task import Attachment
from app.repositories.project_cost_repo import ProjectCostRepository
from app.repositories.task_repo import AttachmentRepository

from app.schemas.payment import ProjectCostResponse
from app.services.number_generator import generate_project_cost_no
from app.services.payable_service import PayableService, validate_payable_amount
from app.services.supplier_service import SupplierService


_MONEY_QUANTUM = Decimal("0.01")


def project_cost_payment_amount(
    amount: Decimal | int | float | str | None,
    debt_amount: Decimal | int | float | str | None,
) -> Decimal:
    """Return the amount paid when a project cost was registered.

    Project costs persist the source total in ``amount`` and the portion that
    enters the payable ledger in ``debt_amount``.  Keep this compatibility
    calculation in one place for list/detail responses.  Invalid historical
    rows are kept readable and never expose a negative paid amount.
    """

    total = Decimal(str(amount or 0)).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    debt = Decimal(str(debt_amount or 0)).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    return max(Decimal("0.00"), total - debt).quantize(
        _MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


class ProjectCostService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectCostRepository(db)
        self.attachment_repo = AttachmentRepository(db)

    async def _sync_document_cost(self, document_id: UUID | None) -> None:
        """Re-calculate order cost when the associated document is an order."""
        if not document_id:
            return
        result = await self.db.execute(
            select(BusinessDocument.doc_type).where(BusinessDocument.id == document_id)
        )
        doc_type = result.scalar_one_or_none()
        if doc_type != "order":
            return
        from app.services.business_document_service import BusinessDocumentService
        order_svc = BusinessDocumentService(self.db, doc_type="order")
        await order_svc.auto_calculate_cost(document_id)

    async def list_costs(
        self,
        page: int,
        page_size: int,
        order_id: UUID | None = None,
        quote_id: UUID | None = None,
        source_type: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        order_item_id: UUID | None = None,
    ) -> tuple[list, int]:
        skip = (page - 1) * page_size
        costs, total = await self.repo.list_costs(
            skip,
            page_size,
            order_id,
            quote_id,
            source_type,
            category,
            date_from,
            date_to,
            order_item_id,
        )
        result = [self._to_dict(c) for c in costs]
        # Populate attachment counts
        if result:
            cost_ids = [c.id for c in costs]
            counts = await self._get_attachment_counts(cost_ids)
            for d in result:
                d["attachment_count"] = counts.get(d["id"], 0)
        return result, total

    @staticmethod
    def _coerce_item_ids(raw_ids) -> list[UUID]:
        if raw_ids is None:
            return []
        if isinstance(raw_ids, (str, UUID)):
            raw_ids = [raw_ids]

        item_ids: list[UUID] = []
        for raw_id in raw_ids:
            try:
                item_ids.append(UUID(str(raw_id)))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError("成本明细ID无效") from exc

        if len(item_ids) != len(set(item_ids)):
            raise ValueError("成本明细不能重复选择")
        return item_ids

    @classmethod
    def _item_scope_request(cls, data: dict) -> tuple[bool, list[UUID]]:
        """Return whether the payload changes item scope and its requested IDs."""
        scalar_refs = [
            data[key]
            for key in ("document_item_id", "order_item_id", "quote_item_id")
            if key in data and data[key] is not None
        ]
        collection_key_present = "order_item_ids" in data
        collection_value = data.get("order_item_ids")
        collection_is_request = collection_key_present and (
            collection_value is not None or not scalar_refs
        )

        if collection_is_request and scalar_refs:
            raise ValueError("不能同时提交单个明细和多明细归属")
        if collection_is_request:
            return True, cls._coerce_item_ids(collection_value)
        if scalar_refs:
            if len(scalar_refs) > 1:
                raise ValueError("一条成本只能使用一种明细归属字段")
            return True, cls._coerce_item_ids(scalar_refs[0])
        if any(key in data for key in ("document_item_id", "order_item_id", "quote_item_id")):
            return True, []
        return False, []

    @staticmethod
    def _item_ids_for_cost(cost: ProjectCost) -> list[UUID]:
        link_ids = {
            link.document_item_id
            for link in (getattr(cost, "item_links", None) or [])
            if link.document_item_id
        }
        if not link_ids and cost.document_item_id:
            link_ids.add(cost.document_item_id)
        return list(link_ids)

    @staticmethod
    def _historical_item_ids_for_cost(cost: ProjectCost) -> set[UUID]:
        historical_ids: set[UUID] = set()
        for link in (getattr(cost, "item_links", None) or []):
            item = getattr(link, "document_item", None)
            lifecycle_status = getattr(item, "lifecycle_status", None)
            if (
                link.document_item_id
                and isinstance(lifecycle_status, str)
                and lifecycle_status != "active"
            ):
                historical_ids.add(link.document_item_id)
        legacy_item = getattr(cost, "document_item", None)
        legacy_status = getattr(legacy_item, "lifecycle_status", None)
        if (
            cost.document_item_id
            and isinstance(legacy_status, str)
            and legacy_status != "active"
        ):
            historical_ids.add(cost.document_item_id)
        return historical_ids

    @staticmethod
    def _set_item_links(cost: ProjectCost, item_ids: list[UUID]) -> None:
        """Replace associations while keeping the old one-item column compatible."""
        cost.document_item_id = item_ids[0] if len(item_ids) == 1 else None
        existing_links = {
            link.document_item_id: link
            for link in (getattr(cost, "item_links", None) or [])
            if link.document_item_id
        }
        cost.item_links = [
            existing_links.get(item_id) or ProjectCostItemLink(document_item_id=item_id)
            for item_id in item_ids
        ]

    async def _resolve_document_item_ids(
        self,
        data: dict,
        document_id: UUID | None,
        document_type: str | None,
        *,
        existing_item_ids: set[UUID] | None = None,
    ) -> tuple[bool, list[UUID]]:
        """Resolve and validate one or more item references for a cost record."""
        scope_requested, item_ids = self._item_scope_request(data)
        if not scope_requested:
            return False, list(existing_item_ids or set())

        if document_type == "order" and data.get("quote_item_id") is not None:
            raise ValueError("订单成本不能关联报价明细")
        if document_type == "quote" and (
            data.get("order_item_id") is not None
            or data.get("order_item_ids")
        ):
            raise ValueError("报价成本不能关联订单明细")

        existing_item_ids = existing_item_ids or set()
        if not item_ids:
            return True, []
        if not document_id:
            raise ValueError("成本明细必须关联订单或报价单")

        result = await self.db.execute(
            select(BusinessDocumentItem).where(
                BusinessDocumentItem.id.in_(item_ids),
                BusinessDocumentItem.document_id == document_id,
            )
        )
        items = list(result.scalars().all())
        items_by_id = {item.id: item for item in items}
        if len(items_by_id) != len(item_ids):
            raise ValueError("成本明细不属于当前业务单据")

        for item_id in item_ids:
            lifecycle_status = getattr(items_by_id[item_id], "lifecycle_status", None)
            if lifecycle_status not in (None, "active") and item_id not in existing_item_ids:
                raise ValueError("只能关联当前有效明细")

        return True, item_ids

    async def get_cost(self, cost_id: UUID) -> dict | None:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            return None
        d = self._to_dict(c)
        atts = await self.attachment_repo.get_by_task("project_cost", cost_id)
        d["attachments"] = [
            {
                "id": str(a.id),
                "filename": a.filename,
                "file_path": a.file_path,
                "file_size": a.file_size,
                "file_type": a.file_type,
                "category": a.category,
                "uploaded_by": str(a.uploaded_by) if a.uploaded_by else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in atts
        ]
        d["attachment_count"] = len(atts)
        return d

    async def create_cost(self, data: dict, created_by: UUID, skip_sync: bool = False) -> dict:
        # Resolve document_id from backward-compat params
        document_id = None
        if data.get("document_id"):
            document_id = UUID(data["document_id"])
        elif data.get("order_id"):
            document_id = UUID(data["order_id"])
        elif data.get("quote_id"):
            document_id = UUID(data["quote_id"])

        customer_id_val = None
        project_name_val = None
        doc_no_val = None
        doc_type_val = None

        if document_id:
            result = await self.db.execute(
                select(BusinessDocument).where(BusinessDocument.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                raise ValueError("业务单据不存在")
            customer_id_val = doc.customer_id
            project_name_val = doc.project_name
            doc_no_val = doc.doc_no
            doc_type_val = doc.doc_type

        # Resolve one or more item IDs from backward-compatible params.
        _, item_ids = await self._resolve_document_item_ids(
            data,
            document_id,
            doc_type_val,
        )

        debt_amount = data.get("debt_amount")
        if debt_amount is not None:
            debt_amount = float(debt_amount)
        else:
            debt_amount = 0
        debt_amount = float(
            validate_payable_amount(
                Decimal(str(data["amount"])),
                Decimal(str(debt_amount)),
            )
        )

        supplier_service = SupplierService(self.db)
        supplier = await supplier_service.resolve_active_supplier(data.get("supplier_id"))
        if supplier is None and data.get("payee_company_name"):
            supplier = await supplier_service.find_unique_active_supplier(
                data.get("payee_company_name")
            )
        payee_company_name = data.get("payee_company_name") or (
            supplier.name if supplier else None
        )

        cost = ProjectCost(
            cost_no=await generate_project_cost_no(self.db),
            document_id=document_id,
            customer_id=customer_id_val,
            category=data["category"],
            amount=data["amount"],
            description=data.get("description"),
            summary=data.get("summary"),
            cost_date=datetime.fromisoformat(data["cost_date"]) if data.get("cost_date") else None,
            receipt_url=data.get("receipt_url"),
            quantity=data.get("quantity"),
            specification=data.get("specification"),
            unit=data.get("unit"),
            unit_price=data.get("unit_price"),
            remark=data.get("remark"),
            document_item_id=item_ids[0] if len(item_ids) == 1 else None,
            payment_method=data.get("payment_method"),
            payee_company_name=payee_company_name,
            supplier_id=supplier.id if supplier else None,
            debt_amount=debt_amount,
            is_debt=debt_amount > 0,
            is_settled=False,
            created_by=created_by,
        )
        # Explicitly set group_name after constructor (SQLAlchemy kwarg issue)
        if data.get("group_name"):
            cost.group_name = data["group_name"]
        self._set_item_links(cost, item_ids)
        await self.repo.create(cost)
        if document_id and not skip_sync:
            await self._sync_document_cost(document_id)
        return self._add_cost_contract({
            "id": str(cost.id),
            "cost_no": cost.cost_no,
            "source_type": doc_type_val,
            "document_id": str(cost.document_id) if cost.document_id else None,
            "doc_no": doc_no_val,
            "order_id": str(cost.document_id) if cost.document_id else None,
            "quote_id": str(cost.document_id) if cost.document_id and doc_type_val == "quote" else None,
            "order_no": doc_no_val if doc_type_val == "order" else None,
            "quote_no": doc_no_val if doc_type_val == "quote" else None,
            "document_item_id": str(cost.document_item_id) if cost.document_item_id else None,
            "order_item_id": str(cost.document_item_id) if cost.document_item_id and doc_type_val == "order" else None,
            "order_item_ids": [str(item_id) for item_id in item_ids] if doc_type_val == "order" else [],
            "quote_item_id": str(cost.document_item_id) if cost.document_item_id and doc_type_val == "quote" else None,
            "item_scopes": [
                {"order_item_id": str(item_id), "order_item_name": None}
                for item_id in item_ids
            ] if doc_type_val == "order" else [],
            "scope_type": "item" if item_ids else "document",
            "group_name": cost.group_name,
            "order_item_name": None,  # populated via document_item relationship on read
            "quote_item_name": None,
            "customer_id": str(cost.customer_id) if cost.customer_id else None,
            "customer_name": None,  # populated by list query via relationship
            "project_name": project_name_val,
            "category": cost.category,
            "amount": float(cost.amount),
            "payment_amount": float(project_cost_payment_amount(cost.amount, cost.debt_amount)),
            "quantity": float(cost.quantity) if cost.quantity else None,
            "specification": cost.specification,
            "unit": cost.unit,
            "unit_price": float(cost.unit_price) if cost.unit_price else None,
            "payment_method": cost.payment_method,
            "payee_company_name": cost.payee_company_name,
            "supplier_id": str(cost.supplier_id) if cost.supplier_id else None,
            "supplier_name": supplier.name if supplier else None,
            "debt_amount": float(cost.debt_amount) if cost.debt_amount else None,
            "is_debt": cost.is_debt,
            "is_settled": cost.is_settled,
            "settled_at": cost.settled_at.isoformat() if cost.settled_at else None,
            "description": cost.description,
            "summary": cost.summary,
            "cost_date": cost.cost_date.isoformat() if cost.cost_date else None,
            "receipt_url": cost.receipt_url,
            "remark": cost.remark,
            "created_by": str(cost.created_by) if cost.created_by else None,
            "created_at": cost.created_at.isoformat() if cost.created_at else None,
        })

    async def update_cost(self, cost_id: UUID, data: dict) -> dict:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            raise ValueError("项目成本记录不存在")

        normalized = dict(data)
        allow_null_fields: set[str] = set()
        if "supplier_id" in normalized:
            supplier = await SupplierService(self.db).resolve_active_supplier(normalized["supplier_id"])
            normalized["supplier_id"] = supplier.id if supplier else None
            allow_null_fields.add("supplier_id")
        for field_name in ("payment_method", "cost_date", "remark", "group_name"):
            if field_name in normalized:
                allow_null_fields.add(field_name)
        item_fields_present = any(
            key in normalized
            for key in ("document_item_id", "order_item_id", "order_item_ids", "quote_item_id")
        )
        if item_fields_present:
            document_type = c.document.doc_type if c.document else None
            if document_type is None and c.document_id:
                result = await self.db.execute(
                    select(BusinessDocument.doc_type).where(BusinessDocument.id == c.document_id)
                )
                document_type = result.scalar_one_or_none()

            existing_item_ids = set(self._item_ids_for_cost(c))
            protected_item_ids = self._historical_item_ids_for_cost(c)
            _, item_ids = await self._resolve_document_item_ids(
                normalized,
                c.document_id,
                document_type,
                existing_item_ids=existing_item_ids,
            )
            if not protected_item_ids.issubset(set(item_ids)):
                raise ValueError("历史明细归属不可移除")
            normalized["document_item_id"] = item_ids[0] if len(item_ids) == 1 else None
            normalized.pop("order_item_id", None)
            normalized.pop("order_item_ids", None)
            normalized.pop("quote_item_id", None)
            self._set_item_links(c, item_ids)

        if "cost_date" in normalized and normalized["cost_date"] is not None:
            normalized["cost_date"] = datetime.fromisoformat(normalized["cost_date"])
        if "amount" in normalized or "debt_amount" in normalized:
            new_amount = Decimal(str(normalized.get("amount", c.amount)))
            new_debt = Decimal(
                str(normalized.get("debt_amount", getattr(c, "debt_amount", 0)) or 0)
            )
            new_debt = validate_payable_amount(new_amount, new_debt)
            normalized["debt_amount"] = new_debt
            normalized["is_debt"] = new_debt > 0
            await PayableService(self.db).validate_source_update(
                "project_cost",
                c.id,
                new_debt,
            )
        if "document_item_id" in normalized and normalized["document_item_id"] is None:
            allow_null_fields.add("document_item_id")
        if allow_null_fields:
            await self.repo.update(
                c,
                normalized,
                allow_null_fields=allow_null_fields,
            )
        else:
            await self.repo.update(c, normalized)
        await self._sync_document_cost(c.document_id)
        # Re-fetch with relationships loaded for response
        c = await self.repo.get_by_id(cost_id)
        return self._to_dict(c)

    async def delete_cost(self, cost_id: UUID) -> None:
        c = await self.repo.get_by_id(cost_id)
        if not c:
            raise ValueError("项目成本记录不存在")
        debt_amount = Decimal(str(getattr(c, "debt_amount", 0) or 0))
        if debt_amount > 0:
            await PayableService(self.db).assert_source_can_be_deleted(
                "project_cost", c.id
            )
        document_id = c.document_id
        await self.repo.soft_delete(c)
        if document_id:
            await self._sync_document_cost(document_id)

    async def batch_delete_costs(self, cost_ids: list[UUID]) -> int:
        from app.models.project_cost import ProjectCost
        from sqlalchemy import select
        # Collect document_ids before deletion for cost sync
        result = await self.db.execute(
            select(ProjectCost)
            .where(ProjectCost.id.in_(cost_ids), ProjectCost.deleted_at.is_(None))
        )
        costs = list(result.scalars().all())
        for cost in costs:
            debt_amount = Decimal(str(getattr(cost, "debt_amount", 0) or 0))
            if debt_amount > 0:
                await PayableService(self.db).assert_source_can_be_deleted(
                    "project_cost", cost.id
                )
        document_ids = {cost.document_id for cost in costs if cost.document_id}
        deleted = await self.repo.batch_soft_delete(cost_ids)
        for did in document_ids:
            await self._sync_document_cost(did)
        return deleted

    async def get_costs_summary(self, document_ids: list[UUID]) -> dict[str, float]:
        """Return {document_id: total_cost} for a batch of documents."""
        return await self.repo.get_costs_summary(document_ids)

    async def get_order_cost_summary(self, order_id: UUID) -> dict:
        """Return manual cost totals split between whole-order and item scope."""
        result = await self.db.execute(
            select(BusinessDocument).where(
                BusinessDocument.id == order_id,
                BusinessDocument.deleted_at.is_(None),
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError("订单不存在")
        if document.doc_type != "order":
            raise ValueError("仅订单支持订单明细成本汇总")

        summary = await self.repo.get_document_item_cost_summary(order_id)
        items = [
            {
                "order_item_id": str(row["document_item_id"]),
                "total_registered": float(Decimal(str(row["amount"] or 0))),
                "record_count": int(row["record_count"] or 0),
            }
            for row in summary["items"]
        ]

        return {
            "order_id": str(order_id),
            "total_registered": float(Decimal(str(summary["total_registered"] or 0))),
            "order_scope_registered": float(Decimal(str(summary["order_scope_registered"] or 0))),
            "item_scope_registered": float(Decimal(str(summary["item_scope_registered"] or 0))),
            "items": items,
        }

    async def list_debts(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        is_settled: bool | None = None,
    ) -> tuple[list, int]:
        """List all cost debts."""
        from sqlalchemy import or_
        from app.models.customer import Customer as CustomerModel

        skip = (page - 1) * page_size
        q = select(ProjectCost).options(
            selectinload(ProjectCost.document),
            selectinload(ProjectCost.item_links).selectinload(
                ProjectCostItemLink.document_item
            ),
            selectinload(ProjectCost.customer),
            selectinload(ProjectCost.supplier),
        ).where(
            ProjectCost.deleted_at.is_(None),
            ProjectCost.is_debt == True,
        )
        if is_settled is not None:
            q = q.where(ProjectCost.is_settled == is_settled)
        if keyword:
            fuzzy = f"%{keyword}%"
            q = q.join(ProjectCost.document).join(ProjectCost.customer, isouter=True).where(
                or_(
                    BusinessDocument.doc_no.ilike(fuzzy),
                    BusinessDocument.project_name.ilike(fuzzy),
                    CustomerModel.name.ilike(fuzzy),
                )
            )

        # Count
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(ProjectCost.created_at.desc()).offset(skip).limit(page_size)
        result = await self.db.execute(q)
        costs = list(result.scalars().all())

        result_list = []
        for c in costs:
            d = self._to_dict(c)
            result_list.append(d)
        return result_list, total

    async def settle_debt(self, cost_id: UUID, settle_data: dict) -> dict:
        """结清成本欠款，不重复计入项目成本。"""
        from datetime import datetime, timezone
        from decimal import Decimal

        c = await self.repo.get_by_id(cost_id, for_update=True)
        if not c:
            raise ValueError("成本记录不存在")
        if not c.is_debt:
            raise ValueError("该记录不是欠款记录")
        if c.is_settled:
            raise ValueError("该欠款已结清")
        settle_amount = Decimal(str(settle_data["settle_amount"]))
        debt_amount = Decimal(str(c.debt_amount or 0))
        if settle_amount != debt_amount:
            raise ValueError(f"结清金额必须等于欠款金额 {debt_amount:.2f} 元")

        c.is_settled = True
        c.settled_at = datetime.now(timezone.utc)
        c.payment_method = settle_data.get("payment_method", c.payment_method or "转账支付")
        if settle_data.get("remark"):
            c.remark = (c.remark or "") + f" [结清: {settle_data['remark']}]"
        await self.db.flush()

        return self._to_dict(c)

    async def import_from_excel(self, file: BytesIO, created_by: UUID, order_id: UUID | None = None, quote_id: UUID | None = None, source_type: str = "order") -> dict:
        """Parse an old or current project-cost workbook.

        The current format is based on the financial fields shown by the UI:
        日期、供应商、支付金额、欠款金额、分类、付款方式、支出总额、说明。
        ``amount`` remains the persisted total and ``debt_amount`` remains the
        amount entering the payable ledger.  The former template is accepted
        during the compatibility window so historical workbooks do not break.
        """
        import openpyxl

        wb = openpyxl.load_workbook(file, read_only=True)
        ws = wb.active
        # Read header row to build column name -> index mapping
        headers = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        if not headers or not headers[0]:
            return {"created": 0, "errors": [{"row": 1, "error": "Excel 文件缺少表头行"}]}
        col_map = {}
        for col_idx, h in enumerate(headers[0]):
            if h is None:
                continue
            name = str(h).strip()
            col_map[name] = col_idx

        created = 0
        synced_doc_ids = set()
        errors = []

        def get_value(row_values, *aliases):
            for alias in aliases:
                idx = col_map.get(alias)
                if idx is not None and idx < len(row_values):
                    return row_values[idx]
            return None

        def text_value(value) -> str:
            return "" if value is None else str(value).strip()

        def number_value(value, label: str) -> Decimal | None:
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            raw = str(value).replace(",", "").replace("¥", "").strip()
            try:
                return Decimal(raw).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"{label}必须是数字") from exc

        def parse_date(value) -> str | None:
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time()).isoformat()
            raw = str(value).strip().replace("/", "-")
            try:
                return datetime.fromisoformat(raw).isoformat()
            except ValueError as exc:
                raise ValueError("日期格式不正确，请使用 YYYY-MM-DD") from exc

        is_current_format = any(
            name in col_map for name in ("支付金额", "支出总额", "供应商", "日期", "分类")
        )

        def parse_row(row_values, require_doc_no: bool) -> dict:
            doc_no = text_value(get_value(row_values, "订单编号", "报价单编号"))
            if require_doc_no and not doc_no:
                raise ValueError("单据编号不能为空")

            category = text_value(get_value(row_values, "分类", "成本类别"))
            payment_method = text_value(get_value(row_values, "付款方式")) or None
            supplier_name = text_value(get_value(row_values, "供应商")) or None
            payee_company_name = text_value(get_value(row_values, "收款公司")) or None
            debt_amount = number_value(get_value(row_values, "欠款金额"), "欠款金额") or Decimal("0.00")
            payment_amount = number_value(get_value(row_values, "支付金额"), "支付金额")
            total_amount = number_value(get_value(row_values, "支出总额"), "支出总额")
            legacy_amount = number_value(get_value(row_values, "金额"), "金额")

            if is_current_format:
                # If a workbook only supplies total + debt, infer the paid
                # portion.  Otherwise the two entered components are the
                # source of truth and total is checked rather than trusted.
                if payment_amount is None and total_amount is not None:
                    payment_amount = total_amount - debt_amount
                elif payment_amount is None and legacy_amount is not None:
                    payment_amount = legacy_amount - debt_amount
                elif payment_amount is None:
                    payment_amount = Decimal("0.00")
                derived_total = payment_amount + debt_amount
                if total_amount is not None and payment_amount is not None and total_amount != derived_total:
                    raise ValueError("支付金额加欠款金额必须等于支出总额")
                total_amount = derived_total
                legacy_fields = {}
            else:
                total_amount = legacy_amount or Decimal("0.00")
                payment_amount = total_amount - debt_amount
                legacy_fields = {
                    "quantity": number_value(get_value(row_values, "数量"), "数量"),
                    "specification": text_value(get_value(row_values, "规格尺寸")) or None,
                    "unit": text_value(get_value(row_values, "单位")) or None,
                    "unit_price": number_value(get_value(row_values, "单价"), "单价"),
                }

            if not category or total_amount <= 0:
                raise ValueError("分类和支出总额(>0)为必填项")
            if payment_amount < 0:
                raise ValueError("支付金额不能小于0")
            debt_amount = validate_payable_amount(total_amount, debt_amount)

            return {
                "doc_no": doc_no,
                "category": category,
                "amount": float(total_amount),
                "debt_amount": float(debt_amount),
                "payment_method": payment_method,
                "supplier_name": supplier_name,
                "payee_company_name": payee_company_name,
                "cost_date": parse_date(get_value(row_values, "日期", "成本日期")),
                "group_name": text_value(get_value(row_values, "分项")) or None,
                "description": text_value(get_value(row_values, "描述")) or None,
                "summary": text_value(get_value(row_values, "成本摘要")) or None,
                "remark": text_value(get_value(row_values, "说明")) or text_value(get_value(row_values, "备注")) or None,
                "legacy_fields": {
                    key: float(value) if isinstance(value, Decimal) else value
                    for key, value in legacy_fields.items()
                },
            }

        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not any(value is not None and str(value).strip() for value in row):
                continue
            try:
                parsed = parse_row(row, require_doc_no=not (order_id or quote_id))
                doc_obj = None
                if order_id or quote_id:
                    target_data = {
                        "source_type": source_type,
                        "order_id": str(order_id) if order_id else None,
                        "quote_id": str(quote_id) if quote_id else None,
                    }
                    synced_doc_ids.add(order_id or quote_id)
                else:
                    doc_result = await self.db.execute(
                        select(BusinessDocument).where(BusinessDocument.doc_no == parsed["doc_no"])
                    )
                    doc_obj = doc_result.scalar_one_or_none()
                    if not doc_obj:
                        raise ValueError(f"单据编号「{parsed['doc_no']}」不存在")
                    target_data = {
                        "source_type": doc_obj.doc_type,
                        "order_id": str(doc_obj.id) if doc_obj.doc_type == "order" else None,
                        "quote_id": str(doc_obj.id) if doc_obj.doc_type == "quote" else None,
                    }
                    synced_doc_ids.add(doc_obj.id)

                supplier = None
                if parsed["supplier_name"]:
                    supplier = await SupplierService(self.db).find_unique_active_supplier(parsed["supplier_name"])
                    if supplier is None:
                        raise ValueError(f"供应商「{parsed['supplier_name']}」不存在，请先在供应商管理中建立")

                target_data.update({
                    "category": parsed["category"],
                    "amount": parsed["amount"],
                    "debt_amount": parsed["debt_amount"],
                    "payment_method": parsed["payment_method"],
                    "supplier_id": supplier.id if supplier else None,
                    "payee_company_name": parsed["payee_company_name"],
                    "cost_date": parsed["cost_date"],
                    "group_name": parsed["group_name"],
                    "description": parsed["description"],
                    "summary": parsed["summary"],
                    "remark": parsed["remark"],
                    **parsed["legacy_fields"],
                })
                await self.create_cost(target_data, created_by, skip_sync=True)
                created += 1
            except Exception as e:
                errors.append({"row": i, "error": str(e)})

        # Batch sync: sync each unique document once
        if synced_doc_ids:
            for did in synced_doc_ids:
                await self._sync_document_cost(did)

        return {"created": created, "errors": errors}

    async def _get_attachment_counts(self, cost_ids: list[UUID]) -> dict[str, int]:
        """Return {cost_id_str: count} for a batch of costs."""
        if not cost_ids:
            return {}
        from sqlalchemy import func
        result = await self.db.execute(
            select(Attachment.related_id, func.count())
            .where(
                Attachment.related_type == "project_cost",
                Attachment.related_id.in_(cost_ids),
            )
            .group_by(Attachment.related_id)
        )
        return {str(row[0]): row[1] for row in result.all()}

    @staticmethod
    def _add_cost_contract(data: dict) -> dict:
        """Attach canonical cost status and object-state capabilities."""
        is_settled = bool(data.get("is_settled"))
        is_debt = bool(data.get("is_debt"))
        if is_settled:
            status_view = make_status_view(
                "settled",
                "已结清",
                tone="success",
                terminal=True,
            )
            settle_reason = "该欠款已结清"
        elif is_debt:
            status_view = make_status_view(
                "debt",
                "待结清",
                tone="warning",
                terminal=False,
            )
            settle_reason = None
        else:
            status_view = make_status_view(
                "registered",
                "已登记",
                tone="info",
                terminal=False,
            )
            settle_reason = "非欠款成本无需结清"
        data["status_view"] = status_view.model_dump(mode="json")
        data["capabilities"] = {
            "settle": make_action_capability(
                is_debt and not is_settled,
                settle_reason,
            ).model_dump(mode="json"),
        }
        return data

    def _to_dict(self, c: ProjectCost) -> dict:
        """Pydantic model_validate + 手动补充关系派生字段和向后兼容别名。"""
        d = ProjectCostResponse.model_validate(c).model_dump(mode="json")
        d["payment_amount"] = float(project_cost_payment_amount(c.amount, c.debt_amount))

        # 从 document 关系取字段
        doc = c.document
        doc_type = doc.doc_type if doc else None
        d["doc_no"] = doc.doc_no if doc else None
        d["doc_type"] = doc_type
        d["source_type"] = doc_type or "order"
        d["project_name"] = doc.project_name if doc else None
        d["customer_name"] = c.customer.name if c.customer else None
        d["supplier_id"] = str(c.supplier_id) if c.supplier_id else None
        d["supplier_name"] = getattr(getattr(c, "supplier", None), "name", None)

        # 从多值归属关系取字段；旧单值字段仅作为迁移窗口的兼容回退。
        item_scopes = []
        for link in (getattr(c, "item_links", None) or []):
            item = getattr(link, "document_item", None)
            if not link.document_item_id:
                continue
            item_scopes.append(
                {
                    "order_item_id": str(link.document_item_id),
                    "order_item_name": getattr(item, "item_name", None),
                }
            )
        if not item_scopes and c.document_item_id:
            item_scopes.append(
                {
                    "order_item_id": str(c.document_item_id),
                    "order_item_name": c.document_item.item_name if c.document_item else None,
                }
            )

        item_scopes = list({scope["order_item_id"]: scope for scope in item_scopes}.values())
        is_order = doc_type == "order"
        d["item_scopes"] = item_scopes if is_order else []
        d["order_item_ids"] = [scope["order_item_id"] for scope in item_scopes] if is_order else []
        d["scope_type"] = "item" if item_scopes else "document"

        # Keep singular fields accurate for old clients; a multi-item record
        # deliberately returns null instead of pretending to belong to one item.
        singular_item_id = item_scopes[0]["order_item_id"] if len(item_scopes) == 1 else None
        singular_item_name = item_scopes[0]["order_item_name"] if len(item_scopes) == 1 else None
        d["document_item_id"] = singular_item_id
        d["document_item_name"] = singular_item_name

        # 向后兼容别名
        doc_id = d.get("document_id")
        item_id = singular_item_id
        item_name = d["document_item_name"]
        d["order_id"] = doc_id
        d["quote_id"] = doc_id if doc_type == "quote" else None
        d["order_no"] = d["doc_no"] if doc_type == "order" else None
        d["quote_no"] = d["doc_no"] if doc_type == "quote" else None
        d["order_item_id"] = item_id if doc_type == "order" else None
        d["quote_item_id"] = item_id if doc_type == "quote" else None
        d["order_item_name"] = item_name if doc_type == "order" else None
        d["quote_item_name"] = item_name if doc_type == "quote" else None
        return self._add_cost_contract(d)
