from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_document import BusinessDocument
from app.models.outsource import OutsourceTask, OutsourceVendor
from app.models.payment import Payment
from app.models.project_cost import ProjectCost
from app.models.finance_reconciliation import FinanceCostOverlapReview


class FinanceCenterService:
    """Read-only projections for the finance landing page."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def receipt_summary(self, start_date: date, end_date: date) -> dict:
        if start_date > end_date or end_date == date.max:
            raise ValueError("收款统计日期范围无效")

        start_at = datetime.combine(start_date, time.min)
        end_at = datetime.combine(end_date + timedelta(days=1), time.min)
        in_period = Payment.paid_at.is_not(None) & (Payment.paid_at >= start_at) & (Payment.paid_at < end_at)
        undated = Payment.paid_at.is_(None)
        row = (await self.db.execute(
            select(
                func.count(Payment.id).filter(in_period).label("period_count"),
                func.coalesce(func.sum(Payment.amount).filter(in_period), 0).label("period_amount"),
                func.count(Payment.id).filter(undated).label("undated_count"),
                func.coalesce(func.sum(Payment.amount).filter(undated), 0).label("undated_amount"),
            ).where(Payment.is_voided.is_(False))
        )).one()

        return {
            "period": {
                "count": int(row.period_count or 0),
                "amount": float(row.period_amount or Decimal("0")),
            },
            "undated": {
                "count": int(row.undated_count or 0),
                "amount": float(row.undated_amount or Decimal("0")),
            },
            "source": "payments",
            "date_basis": "paid_at",
        }

    async def cost_overlap_candidates(self, page: int, page_size: int) -> dict:
        # Keep persisted decisions visible when source fields are corrected.
        cost = ProjectCost.__table__.alias("manual_cost")
        document = BusinessDocument.__table__.alias("cost_document")
        task = OutsourceTask.__table__.alias("completed_outsource_task")
        vendor = OutsourceVendor.__table__.alias("cost_supplier")
        review = FinanceCostOverlapReview.__table__.alias("overlap_review")
        review_probe = FinanceCostOverlapReview.__table__.alias("overlap_review_probe")

        match = (
            (task.c.related_doc_id == cost.c.document_id)
            & (task.c.vendor_id == cost.c.supplier_id)
            & (task.c.total_amount == cost.c.amount)
        )
        category_may_be_outsource = or_(
            cost.c.category.ilike("%外协%"),
            cost.c.category.ilike("%加工%"),
        )
        review_pair = select(literal(1)).select_from(review_probe).where(
            review_probe.c.project_cost_id == cost.c.id,
            review_probe.c.outsource_task_id == task.c.id,
        ).exists()
        candidate_match = and_(
            match,
            (document.c.doc_type == "order"),
            cost.c.document_id.is_not(None),
            cost.c.supplier_id.is_not(None),
            task.c.status.in_(("completed", "settled")),
            category_may_be_outsource,
        )
        candidate_columns = (
            cost.c.document_id.label("document_id"),
            cost.c.id.label("cost_id"),
            cost.c.cost_no,
            cost.c.category,
            cost.c.amount.label("cost_amount"),
            document.c.doc_no,
            document.c.project_name,
            task.c.id.label("task_id"),
            task.c.task_no,
            task.c.task_type,
            task.c.status.label("task_status"),
            task.c.total_amount.label("task_amount"),
            task.c.completed_at,
            vendor.c.name.label("supplier_name"),
            review.c.id.label("review_id"),
            review.c.decision.label("review_decision"),
            review.c.evidence_type.label("evidence_type"),
            review.c.evidence_reference.label("evidence_reference"),
            review.c.note.label("review_note"),
            review.c.reviewed_at.label("reviewed_at"),
        )
        source = cost.join(document, document.c.id == cost.c.document_id).join(
            task, or_(match, review_pair),
        ).join(vendor, vendor.c.id == cost.c.supplier_id).outerjoin(
            review,
            and_(
                review.c.project_cost_id == cost.c.id,
                review.c.outsource_task_id == task.c.id,
            ),
        )
        where = (
            cost.c.deleted_at.is_(None)
            & task.c.deleted_at.is_(None)
            & (document.c.doc_type == "order")
            & cost.c.document_id.is_not(None)
            & cost.c.supplier_id.is_not(None)
            & or_(candidate_match, review.c.id.is_not(None))
        )
        match_rule = case(
            (
                candidate_match,
                "同一订单、同一供应商、相同金额，且项目成本分类包含外协或加工",
            ),
            else_="已复核候选；来源字段已变化，保留原核对记录",
        )
        query = select(*candidate_columns, match_rule.label("match_rule")).select_from(source).where(where)

        total = int((await self.db.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )) or 0)
        rows = (await self.db.execute(
            query.order_by(task.c.completed_at.desc().nulls_last(), cost.c.cost_no, task.c.task_no)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).mappings().all()

        items = []
        for row in rows:
            items.append({
                "row_key": f"{row['cost_id']}:{row['task_id']}",
                "document_id": str(row["document_id"]),
                "cost_id": str(row["cost_id"]),
                "cost_no": row["cost_no"],
                "category": row["category"],
                "cost_amount": float(row["cost_amount"] or 0),
                "document_no": row["doc_no"],
                "project_name": row["project_name"],
                "task_id": str(row["task_id"]),
                "task_no": row["task_no"],
                "task_type": row["task_type"],
                "task_status": row["task_status"],
                "task_amount": float(row["task_amount"] or 0),
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "supplier_name": row["supplier_name"],
                "match_rule": row["match_rule"],
                "review_status": row["review_decision"] or "pending",
                "review_id": str(row["review_id"]) if row["review_id"] else None,
                "evidence_type": row["evidence_type"],
                "evidence_reference": row["evidence_reference"],
                "review_note": row["review_note"],
                "reviewed_at": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}
