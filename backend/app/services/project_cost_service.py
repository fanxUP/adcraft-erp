from datetime import datetime
from decimal import Decimal
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
        cost.item_links = [ProjectCostItemLink(document_item_id=item_id) for item_id in item_ids]

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
            payee_company_name=data.get("payee_company_name"),
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
            "quantity": float(cost.quantity) if cost.quantity else None,
            "specification": cost.specification,
            "unit": cost.unit,
            "unit_price": float(cost.unit_price) if cost.unit_price else None,
            "payment_method": cost.payment_method,
            "payee_company_name": cost.payee_company_name,
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
        allow_null_fields = (
            {"document_item_id"}
            if "document_item_id" in normalized and normalized["document_item_id"] is None
            else set()
        )
        await self.repo.update(
            c,
            normalized,
            allow_null_fields=allow_null_fields,
        )
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
        """Parse Excel file and create ProjectCost records.
        When order_id or quote_id is provided, all rows are assigned to that entity and the
        Excel only needs columns: 成本类别, 金额, 描述(可选), 成本日期(可选), 备注(可选).
        When neither is provided, the Excel must include column: 订单编号/报价单编号, 成本类别, 金额, ...
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

        rows = list(ws.iter_rows(min_row=2, values_only=True))

        created = 0
        synced_doc_ids = set()
        errors = []

        def get(col_name: str, default=None):
            """Get value from row by column name."""
            idx = col_map.get(col_name)
            if idx is None:
                return default
            return row[idx] if idx < len(row) else default

        for i, row in enumerate(rows, start=2):
            if not row:
                continue
            try:
                if order_id or quote_id:
                    # Import within document context — document_id pre-set
                    category = str(get("成本类别") or "").strip()
                    payment_method = str(get("付款方式") or "").strip() or None
                    payee_company_name = str(get("收款公司") or "").strip() or None
                    quantity_val = get("数量")
                    quantity = float(quantity_val) if quantity_val else None
                    specification = str(get("规格尺寸") or "").strip() or None
                    unit = str(get("单位") or "").strip() or None
                    unit_price_val = get("单价")
                    unit_price = float(unit_price_val) if unit_price_val else None
                    amount_val = get("金额")
                    amount = float(amount_val) if amount_val else 0
                    debt_val = get("欠款金额")
                    debt_amount = float(debt_val) if debt_val else 0
                    cost_date_str = str(get("成本日期") or "").strip() or None
                    description = str(get("说明") or "").strip() or None
                    summary = str(get("成本摘要") or "").strip() or None
                    remark = str(get("备注") or "").strip() or None

                    if not category or amount <= 0:
                        errors.append({"row": i, "error": "成本类别和金额(>0)为必填项"})
                        continue

                    cost_date = None
                    if cost_date_str:
                        try:
                            cost_date = datetime.fromisoformat(cost_date_str)
                        except ValueError:
                            cost_date = datetime.strptime(cost_date_str, "%Y-%m-%d")

                    await self.create_cost({
                        "source_type": source_type,
                        "order_id": str(order_id) if order_id else None,
                        "quote_id": str(quote_id) if quote_id else None,
                        "category": category,
                        "amount": amount,
                        "payment_method": payment_method,
                        "payee_company_name": payee_company_name,
                        "quantity": quantity,
                        "specification": specification,
                        "unit": unit,
                        "unit_price": unit_price,
                        "debt_amount": debt_amount,
                        "description": description,
                        "summary": summary,
                        "cost_date": cost_date.isoformat() if cost_date else None,
                        "remark": remark,
                    }, created_by, skip_sync=True)
                    synced_doc_ids.add(order_id or quote_id)
                else:
                    # Standalone import — Excel must include order_no/报价单编号
                    doc_no = str(get("订单编号") or get("报价单编号") or "").strip()
                    if not doc_no:
                        continue
                    category = str(get("成本类别") or "").strip()
                    payment_method = str(get("付款方式") or "").strip() or None
                    payee_company_name = str(get("收款公司") or "").strip() or None
                    quantity_val = get("数量")
                    quantity = float(quantity_val) if quantity_val else None
                    specification = str(get("规格尺寸") or "").strip() or None
                    unit = str(get("单位") or "").strip() or None
                    unit_price_val = get("单价")
                    unit_price = float(unit_price_val) if unit_price_val else None
                    amount_val = get("金额")
                    amount = float(amount_val) if amount_val else 0
                    debt_val = get("欠款金额")
                    debt_amount = float(debt_val) if debt_val else 0
                    cost_date_str = str(get("成本日期") or "").strip() or None
                    description = str(get("说明") or "").strip() or None
                    summary = str(get("成本摘要") or "").strip() or None
                    remark = str(get("备注") or "").strip() or None

                    if not doc_no or not category or amount <= 0:
                        errors.append({"row": i, "error": "单据编号、成本类别和金额(>0)为必填项"})
                        continue

                    # Look up document by doc_no
                    doc_result = await self.db.execute(
                        select(BusinessDocument).where(BusinessDocument.doc_no == doc_no)
                    )
                    doc_obj = doc_result.scalar_one_or_none()
                    if not doc_obj:
                        errors.append({"row": i, "error": f"单据编号「{doc_no}」不存在"})
                        continue

                    cost_date = None
                    if cost_date_str:
                        try:
                            cost_date = datetime.fromisoformat(cost_date_str)
                        except ValueError:
                            cost_date = datetime.strptime(cost_date_str, "%Y-%m-%d")

                    await self.create_cost({
                        "source_type": doc_obj.doc_type,
                        "order_id": str(doc_obj.id),
                        "category": category,
                        "amount": amount,
                        "payment_method": payment_method,
                        "payee_company_name": payee_company_name,
                        "quantity": quantity,
                        "specification": specification,
                        "unit": unit,
                        "unit_price": unit_price,
                        "debt_amount": debt_amount,
                        "description": description,
                        "summary": summary,
                        "cost_date": cost_date.isoformat() if cost_date else None,
                        "remark": remark,
                    }, created_by, skip_sync=True)
                    synced_doc_ids.add(doc_obj.id)
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

        # 从 document 关系取字段
        doc = c.document
        doc_type = doc.doc_type if doc else None
        d["doc_no"] = doc.doc_no if doc else None
        d["doc_type"] = doc_type
        d["source_type"] = doc_type or "order"
        d["project_name"] = doc.project_name if doc else None
        d["customer_name"] = c.customer.name if c.customer else None

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
