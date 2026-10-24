"""Read-only projections: source totals and cash payments have different grains.

Inferred historical payments have no date and are never period cash flow.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, and_, case, cast, func, literal, or_, select, union_all

from app.core.permissions import user_has_permission
from app.models.business_document import BusinessDocument
from app.models.outsource import OutsourcePayment, OutsourceTask, OutsourceVendor
from app.models.payable import PayablePayment
from app.models.finance_reconciliation import FinancePaymentDateReconciliation
from app.models.payment import Expense
from app.models.project_cost import ProjectCost


@dataclass(frozen=True)
class ExpenditureFilters:
    source_type: str | None = None
    keyword: str | None = None
    category: str | None = None
    supplier_id: UUID | None = None
    document_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    date_status: str = "all"
    project_keyword: str | None = None
    department_keyword: str | None = None
    supplier_keyword: str | None = None
    category_keyword: str | None = None
    group_by: str | None = None
    group_key: str | None = None

    def __post_init__(self):
        if self.source_type not in (None, "expense", "project_cost", "outsource"):
            raise ValueError("支出来源无效")
        if self.date_status not in ("all", "confirmed", "unverified"):
            raise ValueError("付款日期状态无效")
        if self.group_by not in (None, "project", "department", "supplier", "category"):
            raise ValueError("支出汇总维度无效")
        if bool(self.group_by) != bool(self.group_key):
            raise ValueError("分组维度和分组值必须同时提供")
        if self.group_key and len(self.group_key) > 512:
            raise ValueError("分组值过长")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("开始日期不能晚于结束日期")
        if self.end_date == date.max:
            raise ValueError("结束日期超出支持范围")


def _money(value):
    return func.coalesce(value, cast(literal(0), Numeric(14, 2)))


class ExpenditureService:
    def __init__(self, db, viewer):
        self.db, self.viewer = db, viewer

    @property
    def available_sources(self):
        if not user_has_permission(self.viewer, "expense:read"):
            return []
        sources = ["expense", "project_cost"]
        if all(user_has_permission(self.viewer, c) for c in (
            "outsource_center:read", "outsource_task:read", "outsource_payment:read", "finance:view_cost",
        )):
            sources.append("outsource")
        return sources

    @staticmethod
    def _columns(kind, source_type, source, source_no, doc, vendor, category,
                 description, source_date, last_payment_date, amount, paid, remaining, undated,
                 registered_paid, status):
        return [
            (literal(kind + ":") + cast(source.c.id, String)).label("row_key"),
            literal(source_type).label("source_type"), literal(kind).label("source_kind"),
            source.c.id.label("source_id"), source_no.label("source_no"),
            doc.c.id.label("document_id"), doc.c.doc_type.label("document_type"),
            doc.c.doc_no.label("doc_no"), doc.c.project_name.label("project_name"),
            doc.c.department.label("department"),
            vendor.c.id.label("supplier_id"),
            func.coalesce(vendor.c.name, source.c.payee_name if kind == "expense" else
                          source.c.payee_company_name if kind in ("project_cost", "outsource_payment") else
                          cast(literal(None), String)).label("supplier_name"),
            category.label("category"), description.label("description"),
            source_date.label("source_date"), last_payment_date.label("last_payment_date"),
            amount.label("amount"),
            paid.label("paid_amount"), remaining.label("remaining_amount"),
            undated.label("undated_paid_amount"), registered_paid.label("registered_paid_amount"),
            status.label("source_status"),
        ]

    def _ledger(self):
        pp = PayablePayment.__table__
        reconciliation = FinancePaymentDateReconciliation.__table__
        op = OutsourcePayment.__table__
        # Display-only date projection; this never backfills historical payment rows.
        payable_paid_at = func.timezone("Asia/Shanghai", func.timezone("UTC", pp.c.paid_at))
        payment_events = [
            select(
                pp.c.source_type.label("source_kind"),
                pp.c.source_id.label("source_id"),
                payable_paid_at.label("paid_at"),
            ).where(pp.c.is_voided.is_(False)),
            select(
                reconciliation.c.source_type.label("source_kind"),
                reconciliation.c.source_id.label("source_id"),
                reconciliation.c.paid_at.label("paid_at"),
            ).where(reconciliation.c.voided_at.is_(None)),
        ]
        if "outsource" in self.available_sources:
            event_reconciliation = reconciliation.alias("latest_outsource_payment_reconciliation")
            effective_outsource_paid_at = func.coalesce(op.c.paid_at, event_reconciliation.c.paid_at)
            payment_events.append(select(
                case((op.c.task_id.is_(None), "outsource_payment"), else_="outsource_task").label("source_kind"),
                case((op.c.task_id.is_(None), op.c.id), else_=op.c.task_id).label("source_id"),
                effective_outsource_paid_at.label("paid_at"),
            ).select_from(op.outerjoin(
                event_reconciliation,
                and_(
                    event_reconciliation.c.source_type == "outsource_payment",
                    event_reconciliation.c.source_id == op.c.id,
                    event_reconciliation.c.voided_at.is_(None),
                ),
            )).where(effective_outsource_paid_at.is_not(None)))
        dated_events = union_all(*payment_events).subquery("expenditure_payment_date_events")
        latest_payment_dates = select(
            dated_events.c.source_kind,
            dated_events.c.source_id,
            func.max(dated_events.c.paid_at).label("last_payment_date"),
        ).group_by(dated_events.c.source_kind, dated_events.c.source_id).subquery("latest_expenditure_payment_dates")
        # ALL history, including voids, prevents resurrecting legacy settlement.
        ps = select(pp.c.source_type, pp.c.source_id,
                    func.sum(case((pp.c.is_voided.is_(False), pp.c.amount), else_=0)).label("paid"),
                    func.count().label("history_count")) \
            .group_by(pp.c.source_type, pp.c.source_id).subquery("payable_totals")
        legacy_allocations = select(
            reconciliation.c.source_type,
            reconciliation.c.source_id,
            func.sum(reconciliation.c.amount).label("allocated"),
        ).where(
            reconciliation.c.voided_at.is_(None),
            reconciliation.c.source_type.in_(("expense", "project_cost", "outsource_task")),
        ).group_by(reconciliation.c.source_type, reconciliation.c.source_id).subquery("legacy_payment_dates")
        branches = []
        for kind, table, number, debt, date_column, document_column in (
            ("expense", Expense.__table__, "expense_no", "payable_amount", "expense_date", None),
            ("project_cost", ProjectCost.__table__, "cost_no", "debt_amount", "cost_date", "document_id"),
        ):
            doc, vendor = BusinessDocument.__table__.alias(kind + "_doc"), OutsourceVendor.__table__.alias(kind + "_vendor")
            join = table.outerjoin(ps, and_(ps.c.source_type == kind, ps.c.source_id == table.c.id))
            latest = latest_payment_dates.alias(kind + "_latest_payment_date")
            join = join.outerjoin(
                latest,
                and_(latest.c.source_kind == kind, latest.c.source_id == table.c.id),
            )
            join = join.outerjoin(
                legacy_allocations,
                and_(legacy_allocations.c.source_type == kind, legacy_allocations.c.source_id == table.c.id),
            )
            join = join.outerjoin(doc, table.c[document_column] == doc.c.id if document_column else literal(False))
            join = join.outerjoin(vendor, table.c.supplier_id == vendor.c.id)
            amount, payable = _money(table.c.amount), _money(table.c[debt])
            inferred = func.greatest(amount - payable, 0)
            legacy = literal(0)
            registered_paid = literal(0)
            if kind == "project_cost":
                legacy = case((and_(table.c.is_settled.is_(True), _money(ps.c.history_count) == 0), payable), else_=0)
                # The amount paid when a project cost is registered uses its selected cost date.
                # Any existing reconciliation allocation takes precedence over this inferred date
                # so historical records remain additive rather than double-counted.
                registered_paid = case(
                    (table.c[date_column].is_not(None), func.greatest(
                        inferred - _money(legacy_allocations.c.allocated), 0,
                    )),
                    else_=0,
                )
            undated = func.greatest(
                inferred + legacy - _money(legacy_allocations.c.allocated) - registered_paid,
                0,
            )
            paid = inferred + legacy + _money(ps.c.paid)
            registered_paid_date = case(
                (registered_paid > 0, table.c[date_column]),
                else_=cast(literal(None), DateTime),
            )
            settled_legacy_date = cast(literal(None), DateTime)
            if kind == "project_cost":
                settled_legacy_date = case(
                    (legacy > 0, table.c.settled_at),
                    else_=cast(literal(None), DateTime),
                )
            branches.append(select(*self._columns(
                kind, kind, table, table.c[number], doc, vendor, table.c.category,
                table.c.description, table.c[date_column],
                func.greatest(registered_paid_date, settled_legacy_date, latest.c.last_payment_date),
                amount, paid,
                func.greatest(payable - legacy - _money(ps.c.paid), 0), undated,
                registered_paid, literal("active"),
            )).select_from(join).where(table.c.deleted_at.is_(None)))
        if "outsource" in self.available_sources:
            task, op = OutsourceTask.__table__, OutsourcePayment.__table__
            task_payment_reconciliation = reconciliation.alias("task_payment_date_reconciliation")
            effective_payment_date = func.coalesce(op.c.paid_at, task_payment_reconciliation.c.paid_at)
            payment_join = op.outerjoin(
                task_payment_reconciliation,
                and_(
                    task_payment_reconciliation.c.source_type == "outsource_payment",
                    task_payment_reconciliation.c.source_id == op.c.id,
                    task_payment_reconciliation.c.voided_at.is_(None),
                ),
            )
            os = select(op.c.task_id, func.sum(op.c.amount).label("paid"),
                        func.sum(case((effective_payment_date.is_(None), op.c.amount), else_=0)).label("undated")) \
                .select_from(payment_join).where(op.c.task_id.is_not(None)).group_by(op.c.task_id).subquery("outsource_totals")
            task_allocations = legacy_allocations.alias("outsource_task_legacy_dates")
            task_latest = latest_payment_dates.alias("outsource_task_latest_payment_date")
            doc, vendor = BusinessDocument.__table__.alias("outsource_doc"), OutsourceVendor.__table__.alias("outsource_vendor")
            join = task.outerjoin(os, os.c.task_id == task.c.id).outerjoin(
                task_allocations,
                and_(task_allocations.c.source_type == "outsource_task", task_allocations.c.source_id == task.c.id),
            ).outerjoin(
                task_latest,
                and_(task_latest.c.source_kind == "outsource_task", task_latest.c.source_id == task.c.id),
            ).outerjoin(doc, task.c.related_doc_id == doc.c.id).outerjoin(vendor, task.c.vendor_id == vendor.c.id)
            inferred = func.greatest(_money(task.c.paid_amount) - _money(os.c.paid), 0)
            paid = _money(os.c.paid) + inferred
            undated_legacy = func.greatest(inferred - _money(task_allocations.c.allocated), 0)
            inactive = or_(task.c.deleted_at.is_not(None), task.c.status == "cancelled")
            branches.append(select(*self._columns(
                "outsource_task", "outsource", task, task.c.task_no, doc, vendor, task.c.task_type,
                task.c.description, func.coalesce(task.c.completed_at, task.c.created_at),
                task_latest.c.last_payment_date, _money(task.c.total_amount), paid,
                case((inactive, 0), else_=func.greatest(_money(task.c.total_amount) - paid, 0)),
                undated_legacy + _money(os.c.undated), literal(0),
                case((task.c.deleted_at.is_not(None), "deleted"), else_=task.c.status),
            )).select_from(join).where(or_(and_(~inactive, task.c.status.in_(("completed", "settled"))), paid > 0)))
            standalone_reconciliation = reconciliation.alias("standalone_payment_date_reconciliation")
            standalone_latest = latest_payment_dates.alias("standalone_latest_payment_date")
            standalone_paid_at = func.coalesce(op.c.paid_at, standalone_reconciliation.c.paid_at)
            doc, vendor = BusinessDocument.__table__.alias("standalone_doc"), OutsourceVendor.__table__.alias("standalone_vendor")
            join = op.outerjoin(
                standalone_reconciliation,
                and_(
                    standalone_reconciliation.c.source_type == "outsource_payment",
                    standalone_reconciliation.c.source_id == op.c.id,
                    standalone_reconciliation.c.voided_at.is_(None),
                ),
            ).outerjoin(
                standalone_latest,
                and_(standalone_latest.c.source_kind == "outsource_payment", standalone_latest.c.source_id == op.c.id),
            ).outerjoin(doc, literal(False)).outerjoin(vendor, op.c.vendor_id == vendor.c.id)
            branches.append(select(*self._columns(
                "outsource_payment", "outsource", op, op.c.payment_no, doc, vendor,
                literal("未关联任务付款"), op.c.remark, standalone_paid_at,
                func.greatest(standalone_paid_at, standalone_latest.c.last_payment_date), op.c.amount, op.c.amount,
                literal(0), case((standalone_paid_at.is_(None), op.c.amount), else_=0), literal(0), literal("standalone"),
            )).select_from(join).where(op.c.task_id.is_(None)))
        return union_all(*branches).subquery("expenditure_ledger")

    def _disbursements(self, ledger):
        metadata = [ledger.c[k] for k in ledger.c.keys() if k not in (
            "row_key", "amount", "paid_amount", "remaining_amount", "undated_paid_amount",
            "registered_paid_amount",
        )]
        source_totals = [
            ledger.c.amount.label("business_amount"),
            ledger.c.paid_amount,
            ledger.c.remaining_amount,
            ledger.c.undated_paid_amount,
        ]
        inferred = ledger.c.undated_paid_amount
        op = OutsourcePayment.__table__
        reconciliation = FinancePaymentDateReconciliation.__table__
        if "outsource" in self.available_sources:
            unverified_payment_date = reconciliation.alias("unverified_outsource_payment_date")
            effective_unverified_paid_at = func.coalesce(op.c.paid_at, unverified_payment_date.c.paid_at)
            unknown_external = select(func.coalesce(func.sum(op.c.amount), 0)).select_from(
                op.outerjoin(
                    unverified_payment_date,
                    and_(
                        unverified_payment_date.c.source_type == "outsource_payment",
                        unverified_payment_date.c.source_id == op.c.id,
                        unverified_payment_date.c.voided_at.is_(None),
                    ),
                )
            ).where(
                op.c.task_id == ledger.c.source_id,
                effective_unverified_paid_at.is_(None),
            ).scalar_subquery()
            inferred = case(
                (ledger.c.source_kind == "outsource_task", func.greatest(inferred - unknown_external, 0)),
                (ledger.c.source_kind == "outsource_payment", 0), else_=inferred,
            )
        branches = [select(
            (literal("inferred:") + ledger.c.row_key).label("row_key"), *metadata, *source_totals,
            literal("historical").label("payment_kind"), cast(literal(None), String).label("payment_no"),
            inferred.label("amount"), cast(literal(None), DateTime).label("paid_at"),
            cast(literal(None), String).label("payment_method"), literal("unverified").label("date_status"),
            cast(literal(None), String).label("reconciliation_id"),
            cast(literal(None), String).label("evidence_type"),
            cast(literal(None), String).label("evidence_reference"),
            cast(literal(None), String).label("reconciliation_note"),
            ledger.c.source_kind.label("reconciliation_source_type"),
            cast(ledger.c.source_id, String).label("reconciliation_source_id"),
        ).where(inferred > 0)]
        branches.append(select(
            (literal("registered:") + ledger.c.row_key).label("row_key"), *metadata, *source_totals,
            literal("historical").label("payment_kind"), literal("登记时已付").label("payment_no"),
            ledger.c.registered_paid_amount.label("amount"), ledger.c.source_date.label("paid_at"),
            cast(literal(None), String).label("payment_method"), literal("confirmed").label("date_status"),
            cast(literal(None), String).label("reconciliation_id"),
            cast(literal(None), String).label("evidence_type"),
            cast(literal(None), String).label("evidence_reference"),
            cast(literal(None), String).label("reconciliation_note"),
            ledger.c.source_kind.label("reconciliation_source_type"),
            cast(ledger.c.source_id, String).label("reconciliation_source_id"),
        ).where(ledger.c.registered_paid_amount > 0))
        pp = PayablePayment.__table__
        join = pp.join(ledger, and_(pp.c.source_type == ledger.c.source_type, pp.c.source_id == ledger.c.source_id))
        paid_at = func.timezone("Asia/Shanghai", func.timezone("UTC", pp.c.paid_at))
        branches.append(select(
            (literal("payable:") + cast(pp.c.id, String)).label("row_key"), *metadata, *source_totals,
            literal("payable").label("payment_kind"), pp.c.payment_no,
            pp.c.amount, paid_at.label("paid_at"), pp.c.payment_method,
            literal("confirmed").label("date_status"),
            cast(literal(None), String).label("reconciliation_id"),
            cast(literal(None), String).label("evidence_type"),
            cast(literal(None), String).label("evidence_reference"),
            cast(literal(None), String).label("reconciliation_note"),
            ledger.c.source_kind.label("reconciliation_source_type"),
            cast(ledger.c.source_id, String).label("reconciliation_source_id"),
        ).select_from(join).where(pp.c.is_voided.is_(False)))
        legacy = reconciliation.alias("legacy_date_allocations")
        legacy_join = legacy.join(
            ledger,
            and_(legacy.c.source_type == ledger.c.source_kind, legacy.c.source_id == ledger.c.source_id),
        )
        branches.append(select(
            (literal("reconciled:") + cast(legacy.c.id, String)).label("row_key"), *metadata, *source_totals,
            literal("reconciled_legacy").label("payment_kind"),
            literal("历史已付核对").label("payment_no"),
            legacy.c.amount,
            legacy.c.paid_at,
            cast(literal(None), String).label("payment_method"),
            literal("confirmed").label("date_status"),
            cast(legacy.c.id, String).label("reconciliation_id"),
            legacy.c.evidence_type,
            legacy.c.evidence_reference,
            legacy.c.note.label("reconciliation_note"),
            legacy.c.source_type.label("reconciliation_source_type"),
            cast(legacy.c.source_id, String).label("reconciliation_source_id"),
        ).select_from(legacy_join).where(
            legacy.c.voided_at.is_(None),
            legacy.c.source_type.in_(("expense", "project_cost", "outsource_task")),
        ))
        if "outsource" in self.available_sources:
            payment_reconciliation = reconciliation.alias("outsource_payment_date_details")
            effective_paid_at = func.coalesce(op.c.paid_at, payment_reconciliation.c.paid_at)
            join = op.outerjoin(
                payment_reconciliation,
                and_(
                    payment_reconciliation.c.source_type == "outsource_payment",
                    payment_reconciliation.c.source_id == op.c.id,
                    payment_reconciliation.c.voided_at.is_(None),
                ),
            ).join(ledger, and_(ledger.c.source_type == "outsource", or_(
                and_(ledger.c.source_kind == "outsource_task", ledger.c.source_id == op.c.task_id),
                and_(ledger.c.source_kind == "outsource_payment", ledger.c.source_id == op.c.id, op.c.task_id.is_(None)),
            )))
            branches.append(select(
                (literal("outsource:") + cast(op.c.id, String)).label("row_key"), *metadata, *source_totals,
                literal("outsource").label("payment_kind"), op.c.payment_no,
                op.c.amount, effective_paid_at.label("paid_at"), op.c.payment_method,
                case((effective_paid_at.is_(None), "unverified"), else_="confirmed").label("date_status"),
                cast(payment_reconciliation.c.id, String).label("reconciliation_id"),
                payment_reconciliation.c.evidence_type,
                payment_reconciliation.c.evidence_reference,
                payment_reconciliation.c.note.label("reconciliation_note"),
                literal("outsource_payment").label("reconciliation_source_type"),
                cast(op.c.id, String).label("reconciliation_source_id"),
            ).select_from(join))
        return union_all(*branches).subquery("expenditure_disbursements")

    @staticmethod
    def _dimension_projection(table, dimension):
        if dimension == "project":
            document_id = table.c.document_id
            project_label = func.concat_ws(
                " - ", func.nullif(table.c.doc_no, ""), func.nullif(table.c.project_name, ""),
            )
            key = case(
                (document_id.is_not(None), literal("document:") + cast(document_id, String)),
                else_=literal("unlinked"),
            )
            label = case(
                (document_id.is_not(None), func.nullif(project_label, "")),
                else_=literal("未关联项目"),
            )
            return key, func.coalesce(label, literal("未命名项目"))

        if dimension == "department":
            value = func.nullif(func.btrim(func.coalesce(table.c.department, "")), "")
            key = case(
                (value.is_not(None), literal("department:value:") + value),
                else_=literal("department:unassigned"),
            )
            return key, func.coalesce(value, literal("未填写"))

        if dimension == "supplier":
            value = func.nullif(func.btrim(func.coalesce(table.c.supplier_name, "")), "")
            key = case(
                (table.c.supplier_id.is_not(None), literal("supplier:") + cast(table.c.supplier_id, String)),
                else_=literal("payee:") + func.coalesce(value, ""),
            )
            label = func.coalesce(value, literal("未填写"))
            return key, label

        if dimension == "category":
            category = func.coalesce(table.c.category, "")
            key = literal("source:") + table.c.source_type + literal(":") + category
            localized = case(
                (and_(table.c.source_type == "outsource", category == "design"), "设计"),
                (and_(table.c.source_type == "outsource", category == "production"), "制作"),
                (and_(table.c.source_type == "outsource", category == "installation"), "安装"),
                (and_(table.c.source_type == "outsource", category == "transport"), "运输"),
                else_=func.coalesce(func.nullif(table.c.category, ""), "未分类"),
            )
            return key, localized

        raise ValueError("支出汇总维度无效")

    @staticmethod
    def _predicates(table, filters, view, *, dates=True):
        conditions = []
        for key in ("source_type", "category", "supplier_id", "document_id"):
            value = getattr(filters, key)
            if value is not None:
                conditions.append(table.c[key] == value)
        if filters.keyword and filters.keyword.strip():
            conditions.append(or_(*(table.c[k].contains(filters.keyword.strip(), autoescape=True)
                                   for k in ("source_no", "doc_no", "project_name", "supplier_name", "description"))))
        if filters.project_keyword and filters.project_keyword.strip():
            value = filters.project_keyword.strip()
            conditions.append(or_(
                table.c.doc_no.contains(value, autoescape=True),
                table.c.project_name.contains(value, autoescape=True),
            ))
        if filters.department_keyword and filters.department_keyword.strip():
            conditions.append(table.c.department.contains(filters.department_keyword.strip(), autoescape=True))
        if filters.supplier_keyword and filters.supplier_keyword.strip():
            conditions.append(table.c.supplier_name.contains(filters.supplier_keyword.strip(), autoescape=True))
        if filters.category_keyword and filters.category_keyword.strip():
            _, display_category = ExpenditureService._dimension_projection(table, "category")
            value = filters.category_keyword.strip()
            conditions.append(or_(
                table.c.category.contains(value, autoescape=True),
                display_category.contains(value, autoescape=True),
            ))
        if filters.group_key is not None:
            if view != "disbursements":
                raise ValueError("分组下钻仅支持付款记录")
            dimension_key, _ = ExpenditureService._dimension_projection(table, filters.group_by)
            conditions.append(dimension_key == filters.group_key)
        if view == "disbursements" and dates and filters.date_status != "all":
            conditions.append(table.c.date_status == filters.date_status)
        if dates:
            column = table.c.last_payment_date if view == "ledger" else table.c.paid_at
            if filters.start_date:
                conditions.append(column >= datetime.combine(filters.start_date, datetime.min.time()))
            if filters.end_date:
                conditions.append(column < datetime.combine(filters.end_date + timedelta(days=1), datetime.min.time()))
        return conditions

    async def list_summary(self, group_by, page=1, page_size=20, filters=None):
        filters = filters or ExpenditureFilters()
        sources = self.available_sources
        if not sources or (filters.source_type and filters.source_type not in sources):
            raise PermissionError("没有查看该支出来源的权限")
        if group_by not in ("project", "department", "supplier", "category"):
            raise ValueError("支出汇总维度无效")
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")

        disbursements = self._disbursements(self._ledger())
        conditions = self._predicates(disbursements, filters, "disbursements")
        conditions.extend((
            disbursements.c.date_status == "confirmed",
            disbursements.c.paid_at.is_not(None),
        ))
        base = select(disbursements).where(*conditions).cte("dated_expenditure_payments")
        dimension_key, label = self._dimension_projection(base, group_by)
        business_key = func.concat(base.c.source_kind, literal(":"), cast(base.c.source_id, String))

        grouped = select(
            dimension_key.label("dimension_key"),
            label.label("label"),
            (func.min(base.c.source_type) if group_by == "category" else cast(literal(None), String)).label("source_type"),
            (func.min(base.c.category) if group_by == "category" else cast(literal(None), String)).label("category"),
            func.coalesce(func.sum(base.c.amount), 0).label("period_paid_amount"),
            func.count().label("payment_count"),
            func.count(func.distinct(business_key)).label("business_count"),
        ).group_by(dimension_key, label).cte("expenditure_dimension_groups")
        overall = select(
            func.coalesce(func.sum(base.c.amount), 0).label("period_paid_amount"),
            func.count().label("payment_count"),
            func.count(func.distinct(business_key)).label("business_count"),
        ).cte("expenditure_dimension_overall")
        group_total = select(func.count().label("total")).select_from(grouped).cte("expenditure_dimension_count")
        page_rows = select(grouped).order_by(
            grouped.c.period_paid_amount.desc(), grouped.c.dimension_key.asc(),
        ).offset((page - 1) * page_size).limit(page_size).cte("expenditure_dimension_page")
        statement = select(
            page_rows.c.dimension_key,
            page_rows.c.label,
            page_rows.c.source_type,
            page_rows.c.category,
            page_rows.c.period_paid_amount,
            page_rows.c.payment_count,
            page_rows.c.business_count,
            overall.c.period_paid_amount.label("summary_period_paid_amount"),
            overall.c.payment_count.label("summary_payment_count"),
            overall.c.business_count.label("summary_business_count"),
            group_total.c.total.label("summary_total"),
        ).select_from(
            overall.join(group_total, literal(True)).outerjoin(page_rows, literal(True))
        ).order_by(page_rows.c.period_paid_amount.desc().nulls_last(), page_rows.c.dimension_key.asc())
        records = (await self.db.execute(statement)).mappings().all()
        first = records[0]
        summary = {
            "period_paid_amount": float(first["summary_period_paid_amount"] or 0),
            "payment_count": int(first["summary_payment_count"] or 0),
            "business_count": int(first["summary_business_count"] or 0),
        }
        items = []
        for record in records:
            if record["dimension_key"] is None:
                continue
            items.append({
                "dimension_key": record["dimension_key"],
                "label": record["label"],
                "source_type": record["source_type"],
                "category": record["category"],
                "period_paid_amount": float(record["period_paid_amount"] or 0),
                "payment_count": int(record["payment_count"] or 0),
                "business_count": int(record["business_count"] or 0),
            })
        return {
            "items": items,
            "total": int(first["summary_total"] or 0),
            "page": page,
            "page_size": page_size,
            "summary": summary,
            "available_sources": sources,
        }

    async def list_records(self, view, page=1, page_size=20, filters=None):
        filters = filters or ExpenditureFilters()
        sources = self.available_sources
        if not sources or (filters.source_type and filters.source_type not in sources):
            raise PermissionError("没有查看该支出来源的权限")
        if view not in ("ledger", "disbursements") or page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        ledger = self._ledger()
        if view == "ledger":
            table = select(*(
                ledger.c[key] for key in ledger.c.keys() if key != "registered_paid_amount"
            )).subquery("expenditure_ledger_public")
        else:
            table = self._disbursements(ledger)
        # Reuse one projection and one statement snapshot for page + totals.
        # A concurrent payment cannot land between the summary and list reads.
        table = select(table).where(*self._predicates(table, filters, view, dates=False)).cte("expenditure_view")
        predicates = self._predicates(table, filters, view)
        totals = [func.count().label("total"), func.coalesce(func.sum(table.c.amount), 0).label("amount")]
        if view == "ledger":
            totals += [func.coalesce(func.sum(table.c[k]), 0).label(k) for k in ("paid_amount", "remaining_amount", "undated_paid_amount")]
        else:
            totals += [func.coalesce(func.sum(case((table.c.date_status == "confirmed", table.c.amount), else_=0)), 0).label("confirmed_paid_amount")]
        aggregate = select(*totals).where(*predicates).subquery("filtered_totals")
        summary_columns = [aggregate.c[k].label("summary_" + k) for k in aggregate.c.keys()]
        order_date = table.c.last_payment_date if view == "ledger" else table.c.paid_at
        paged = select(table).where(*predicates).order_by(
            order_date.desc().nulls_last(), table.c.row_key.asc(),
        ).offset((page - 1) * page_size).limit(page_size).subquery("paged_records")
        join = aggregate.outerjoin(paged, literal(True))
        if view == "disbursements":
            unverified = select(
                func.count().label("count"), func.coalesce(func.sum(table.c.amount), 0).label("amount"),
            ).where(table.c.date_status == "unverified").subquery("unverified_totals")
            join = join.join(unverified, literal(True))
            summary_columns += [unverified.c.amount.label("summary_unverified_paid_amount"),
                                unverified.c.count.label("summary_unverified_count")]
        page_date = paged.c.last_payment_date if view == "ledger" else paged.c.paid_at
        records = (await self.db.execute(select(paged, *summary_columns).select_from(join).order_by(
            page_date.desc().nulls_last(), paged.c.row_key.asc(),
        ))).mappings().all()
        first = records[0]  # Aggregate always returns one row, even for empty pages.
        summary = {column.key.removeprefix("summary_"): float(first[column.key] or 0)
                   for column in summary_columns if column.key != "summary_total"}
        if view == "disbursements":
            summary["unverified_count"] = int(summary["unverified_count"])
        rows = []
        for record in records:
            if record["row_key"] is None:
                continue
            row = {key: record[key] for key in paged.c.keys()}
            for key, value in row.items():
                if isinstance(value, UUID):
                    row[key] = str(value)
                elif isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    row[key] = float(value)
            rows.append(row)
        return {"items": rows, "total": first["summary_total"], "page": page,
                "page_size": page_size, "summary": summary, "available_sources": sources}
