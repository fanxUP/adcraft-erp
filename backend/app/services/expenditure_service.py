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

    def __post_init__(self):
        if self.source_type not in (None, "expense", "project_cost", "outsource"):
            raise ValueError("支出来源无效")
        if self.date_status not in ("all", "confirmed", "unverified"):
            raise ValueError("付款日期状态无效")
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
                 description, source_date, amount, paid, remaining, undated, status):
        return [
            (literal(kind + ":") + cast(source.c.id, String)).label("row_key"),
            literal(source_type).label("source_type"), literal(kind).label("source_kind"),
            source.c.id.label("source_id"), source_no.label("source_no"),
            doc.c.id.label("document_id"), doc.c.doc_type.label("document_type"),
            doc.c.doc_no.label("doc_no"), doc.c.project_name.label("project_name"),
            vendor.c.id.label("supplier_id"),
            func.coalesce(vendor.c.name, source.c.payee_name if kind == "expense" else
                          source.c.payee_company_name if kind in ("project_cost", "outsource_payment") else
                          cast(literal(None), String)).label("supplier_name"),
            category.label("category"), description.label("description"),
            source_date.label("source_date"), amount.label("amount"),
            paid.label("paid_amount"), remaining.label("remaining_amount"),
            undated.label("undated_paid_amount"), status.label("source_status"),
        ]

    def _ledger(self):
        pp = PayablePayment.__table__
        # ALL history, including voids, prevents resurrecting legacy settlement.
        ps = select(pp.c.source_type, pp.c.source_id,
                    func.sum(case((pp.c.is_voided.is_(False), pp.c.amount), else_=0)).label("paid"),
                    func.count().label("history_count")) \
            .group_by(pp.c.source_type, pp.c.source_id).subquery("payable_totals")
        branches = []
        for kind, table, number, debt, date_column, document_column in (
            ("expense", Expense.__table__, "expense_no", "payable_amount", "expense_date", None),
            ("project_cost", ProjectCost.__table__, "cost_no", "debt_amount", "cost_date", "document_id"),
        ):
            doc, vendor = BusinessDocument.__table__.alias(kind + "_doc"), OutsourceVendor.__table__.alias(kind + "_vendor")
            join = table.outerjoin(ps, and_(ps.c.source_type == kind, ps.c.source_id == table.c.id))
            join = join.outerjoin(doc, table.c[document_column] == doc.c.id if document_column else literal(False))
            join = join.outerjoin(vendor, table.c.supplier_id == vendor.c.id)
            amount, payable = _money(table.c.amount), _money(table.c[debt])
            inferred = func.greatest(amount - payable, 0)
            legacy = literal(0)
            if kind == "project_cost":
                legacy = case((and_(table.c.is_settled.is_(True), _money(ps.c.history_count) == 0), payable), else_=0)
            undated, paid = inferred + legacy, inferred + legacy + _money(ps.c.paid)
            branches.append(select(*self._columns(
                kind, kind, table, table.c[number], doc, vendor, table.c.category,
                table.c.description, table.c[date_column], amount, paid,
                func.greatest(payable - legacy - _money(ps.c.paid), 0), undated, literal("active"),
            )).select_from(join).where(table.c.deleted_at.is_(None)))
        if "outsource" in self.available_sources:
            task, op = OutsourceTask.__table__, OutsourcePayment.__table__
            os = select(op.c.task_id, func.sum(op.c.amount).label("paid"),
                        func.sum(case((op.c.paid_at.is_(None), op.c.amount), else_=0)).label("undated")) \
                .where(op.c.task_id.is_not(None)).group_by(op.c.task_id).subquery("outsource_totals")
            doc, vendor = BusinessDocument.__table__.alias("outsource_doc"), OutsourceVendor.__table__.alias("outsource_vendor")
            join = task.outerjoin(os, os.c.task_id == task.c.id).outerjoin(doc, task.c.related_doc_id == doc.c.id).outerjoin(vendor, task.c.vendor_id == vendor.c.id)
            inferred = func.greatest(_money(task.c.paid_amount) - _money(os.c.paid), 0)
            paid = _money(os.c.paid) + inferred
            inactive = or_(task.c.deleted_at.is_not(None), task.c.status == "cancelled")
            branches.append(select(*self._columns(
                "outsource_task", "outsource", task, task.c.task_no, doc, vendor, task.c.task_type,
                task.c.description, func.coalesce(task.c.completed_at, task.c.created_at),
                _money(task.c.total_amount), paid,
                case((inactive, 0), else_=func.greatest(_money(task.c.total_amount) - paid, 0)),
                inferred + _money(os.c.undated),
                case((task.c.deleted_at.is_not(None), "deleted"), else_=task.c.status),
            )).select_from(join).where(or_(and_(~inactive, task.c.status.in_(("completed", "settled"))), paid > 0)))
            doc, vendor = BusinessDocument.__table__.alias("standalone_doc"), OutsourceVendor.__table__.alias("standalone_vendor")
            join = op.outerjoin(doc, literal(False)).outerjoin(vendor, op.c.vendor_id == vendor.c.id)
            branches.append(select(*self._columns(
                "outsource_payment", "outsource", op, op.c.payment_no, doc, vendor,
                literal("未关联任务付款"), op.c.remark, op.c.paid_at, op.c.amount, op.c.amount,
                literal(0), case((op.c.paid_at.is_(None), op.c.amount), else_=0), literal("standalone"),
            )).select_from(join).where(op.c.task_id.is_(None)))
        return union_all(*branches).subquery("expenditure_ledger")

    def _disbursements(self, ledger):
        metadata = [ledger.c[k] for k in ledger.c.keys() if k not in ("row_key", "amount", "paid_amount", "remaining_amount", "undated_paid_amount")]
        inferred = ledger.c.undated_paid_amount
        op = OutsourcePayment.__table__
        if "outsource" in self.available_sources:
            unknown_external = select(func.coalesce(func.sum(op.c.amount), 0)).where(
                op.c.task_id == ledger.c.source_id, op.c.paid_at.is_(None),
            ).scalar_subquery()
            inferred = case(
                (ledger.c.source_kind == "outsource_task", func.greatest(inferred - unknown_external, 0)),
                (ledger.c.source_kind == "outsource_payment", 0), else_=inferred,
            )
        branches = [select(
            (literal("inferred:") + ledger.c.row_key).label("row_key"), *metadata,
            literal("historical").label("payment_kind"), cast(literal(None), String).label("payment_no"),
            inferred.label("amount"), cast(literal(None), DateTime).label("paid_at"),
            cast(literal(None), String).label("payment_method"), literal("unverified").label("date_status"),
        ).where(inferred > 0)]
        pp = PayablePayment.__table__
        join = pp.join(ledger, and_(pp.c.source_type == ledger.c.source_type, pp.c.source_id == ledger.c.source_id))
        paid_at = func.timezone("Asia/Shanghai", func.timezone("UTC", pp.c.paid_at))
        branches.append(select(
            (literal("payable:") + cast(pp.c.id, String)).label("row_key"), *metadata,
            literal("payable").label("payment_kind"), pp.c.payment_no,
            pp.c.amount, paid_at.label("paid_at"), pp.c.payment_method,
            literal("confirmed").label("date_status"),
        ).select_from(join).where(pp.c.is_voided.is_(False)))
        if "outsource" in self.available_sources:
            join = op.join(ledger, and_(ledger.c.source_type == "outsource", or_(
                and_(ledger.c.source_kind == "outsource_task", ledger.c.source_id == op.c.task_id),
                and_(ledger.c.source_kind == "outsource_payment", ledger.c.source_id == op.c.id, op.c.task_id.is_(None)),
            )))
            branches.append(select(
                (literal("outsource:") + cast(op.c.id, String)).label("row_key"), *metadata,
                literal("outsource").label("payment_kind"), op.c.payment_no,
                op.c.amount, op.c.paid_at, op.c.payment_method,
                case((op.c.paid_at.is_(None), "unverified"), else_="confirmed").label("date_status"),
            ).select_from(join))
        return union_all(*branches).subquery("expenditure_disbursements")

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
        if view == "disbursements" and dates and filters.date_status != "all":
            conditions.append(table.c.date_status == filters.date_status)
        if dates:
            column = table.c.source_date if view == "ledger" else table.c.paid_at
            if filters.start_date:
                conditions.append(column >= datetime.combine(filters.start_date, datetime.min.time()))
            if filters.end_date:
                conditions.append(column < datetime.combine(filters.end_date + timedelta(days=1), datetime.min.time()))
        return conditions

    async def list_records(self, view, page=1, page_size=20, filters=None):
        filters = filters or ExpenditureFilters()
        sources = self.available_sources
        if not sources or (filters.source_type and filters.source_type not in sources):
            raise PermissionError("没有查看该支出来源的权限")
        if view not in ("ledger", "disbursements") or page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        ledger = self._ledger()
        table = ledger if view == "ledger" else self._disbursements(ledger)
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
        order_date = table.c.source_date if view == "ledger" else table.c.paid_at
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
        page_date = paged.c.source_date if view == "ledger" else paged.c.paid_at
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
