from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.business_document import BusinessDocument
from app.models.payment import Payment
from app.models.task import DesignTask, ProductionTask, InstallationTask
from app.models.customer import Customer
from app.models.contract import Contract, ContractDocument
from app.services.business_document_service import BusinessDocumentService
from app.services.vehicle_dashboard_service import VehicleDashboardService


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self) -> dict:
        now = datetime.now()
        today = now.date()
        month_start = today.replace(day=1)

        today_start = datetime(today.year, today.month, today.day)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        month_start_dt = datetime(month_start.year, month_start.month, 1)

        today_orders = await self._sum_orders(today_start, today_end)
        month_orders = await self._sum_orders(month_start_dt, now)

        today_payments = await self._sum_payments(today_start, today_end)
        month_payments = await self._sum_payments(month_start_dt, now)

        month_unpaid = await self._calc_month_unpaid(month_start_dt, now)

        pending_design = await self._count_tasks(DesignTask, ["pending", "designing", "pending_review", "revision"])
        pending_production = await self._count_tasks(ProductionTask, ["pending", "queued", "in_progress", "qc_check", "rework"])
        pending_installation = await self._count_tasks(InstallationTask, ["pending", "assigned", "in_progress", "pending_acceptance"])

        overdue_orders = await self._count_overdue_orders()

        customer_debt_ranking = await self._customer_debt_ranking()

        return {
            "today_order_amount": float(today_orders or 0),
            "today_payment_amount": float(today_payments or 0),
            "month_order_amount": float(month_orders or 0),
            "month_payment_amount": float(month_payments or 0),
            "month_unpaid_amount": float(month_unpaid or 0),
            "pending_design_count": pending_design,
            "pending_production_count": pending_production,
            "pending_installation_count": pending_installation,
            "overdue_order_count": overdue_orders,
            "customer_debt_ranking": customer_debt_ranking,
        }

    async def get_daily_report(self, report_date: str | None = None) -> dict:
        if report_date:
            d = datetime.fromisoformat(report_date)
        else:
            d = datetime.now()
        day_start = datetime(d.year, d.month, d.day)
        day_end = datetime(d.year, d.month, d.day, 23, 59, 59)

        orders = await self._list_orders_in_range(day_start, day_end)
        payments = await self._list_payments_in_range(day_start, day_end)
        new_customers = await self._count_new_customers(day_start, day_end)

        # 车辆与安装运输部分
        vehicle_svc = VehicleDashboardService(self.db)
        vehicle_report = await vehicle_svc.get_daily_report(report_date)

        return {
            "date": d.strftime("%Y-%m-%d"),
            "order_count": len(orders),
            "order_amount": float(sum(o.total_amount for o in orders)),
            "payment_count": len(payments),
            "payment_amount": float(sum(p.amount for p in payments)),
            "new_customer_count": new_customers,
            "orders": [BusinessDocumentService._to_ref(o) for o in orders],
            "payments": [
                {"id": str(p.id), "payment_no": p.payment_no, "amount": float(p.amount),
                 "payment_method": p.payment_method, "is_voided": p.is_voided}
                for p in payments
            ],
            "vehicle": vehicle_report,
        }

    async def get_monthly_report(self, year: int | None = None, month: int | None = None) -> dict:
        now = datetime.now()
        y = year or now.year
        m = month or now.month
        month_start = datetime(y, m, 1)
        if m == 12:
            month_end = datetime(y + 1, 1, 1)
        else:
            month_end = datetime(y, m + 1, 1)

        orders = await self._list_orders_in_range(month_start, month_end)
        payments = await self._list_payments_in_range(month_start, month_end)

        order_amount = float(sum(o.total_amount for o in orders))
        payment_amount = float(sum(p.amount for p in payments))

        status_breakdown = {}
        for o in orders:
            s = o.status
            status_breakdown[s] = status_breakdown.get(s, 0) + 1

        return {
            "year": y,
            "month": m,
            "order_count": len(orders),
            "order_amount": order_amount,
            "payment_count": len(payments),
            "payment_amount": payment_amount,
            "unpaid_amount": order_amount - payment_amount,
            "status_breakdown": status_breakdown,
            "orders": [BusinessDocumentService._to_ref(o) for o in orders],
        }

    async def get_customer_debt(self) -> list:
        """Return all customers with their contracts, orders and quotes for the receivables overview."""
        # Fetch all active customers
        c_result = await self.db.execute(
            select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.name)
        )
        customers = c_result.scalars().all()

        if not customers:
            return []

        customer_ids = [c.id for c in customers]

        # Batch-fetch all contracts grouped by customer
        contracts_result = await self.db.execute(
            select(Contract)
            .where(Contract.deleted_at.is_(None), Contract.customer_id.in_(customer_ids))
            .order_by(Contract.created_at.desc())
        )
        all_contracts = contracts_result.scalars().all()

        # Batch-fetch all orders grouped by customer
        orders_result = await self.db.execute(
            select(BusinessDocument)
            .where(BusinessDocument.deleted_at.is_(None), BusinessDocument.doc_type == "order",
                   BusinessDocument.customer_id.in_(customer_ids))
            .order_by(BusinessDocument.created_at.desc())
        )
        all_orders = orders_result.scalars().all()

        # Batch-fetch all quotes grouped by customer (exclude converted ones)
        quotes_result = await self.db.execute(
            select(BusinessDocument)
            .where(BusinessDocument.deleted_at.is_(None), BusinessDocument.doc_type == "quote",
                   BusinessDocument.customer_id.in_(customer_ids), BusinessDocument.status != "converted")
            .order_by(BusinessDocument.created_at.desc())
        )
        all_quotes = quotes_result.scalars().all()

        # Batch-fetch last payment date per customer
        lp_result = await self.db.execute(
            select(
                Payment.customer_id,
                func.max(Payment.paid_at).label("last_payment"),
            )
            .where(Payment.customer_id.in_(customer_ids), Payment.is_voided == False)
            .group_by(Payment.customer_id)
        )
        last_payments = {r.customer_id: r.last_payment for r in lp_result.all()}

        # Batch-fetch all contract-document links to know which docs are contract-linked
        # Two tables: contract_documents (常规合同) + framework_contract_project_documents (框架合同)
        from app.models.contract import ContractDocument as CD
        from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument as FCPD
        all_contract_ids = [ct.id for ct in all_contracts]
        linked_doc_ids: set[UUID] = set()
        if all_contract_ids:
            # 常规合同关联的单据
            cd_result = await self.db.execute(
                select(CD.document_id).where(CD.contract_id.in_(all_contract_ids))
            )
            linked_doc_ids = {row[0] for row in cd_result.all()}
            # 框架合同项目关联的单据（同时记录 contract_id → document_ids 映射，用于填充合同下的 orders/quotes）
            fw_contract_ids = [ct.id for ct in all_contracts if ct.contract_type == "框架合同"]
            fw_doc_ids_by_contract: dict[UUID, set[UUID]] = {}
            if fw_contract_ids:
                fcpd_result = await self.db.execute(
                    select(FrameworkContractProject.contract_id, FCPD.document_id)
                    .select_from(FCPD)
                    .join(FrameworkContractProject, FCPD.project_id == FrameworkContractProject.id)
                    .where(FrameworkContractProject.contract_id.in_(fw_contract_ids))
                )
                for contract_id, doc_id in fcpd_result.all():
                    linked_doc_ids.add(doc_id)
                    fw_doc_ids_by_contract.setdefault(contract_id, set()).add(doc_id)

        # Batch-fetch paid_amount per contract from actual payments on linked orders
        contract_ids = all_contract_ids
        paid_map: dict[UUID, float] = {}
        if contract_ids:
            paid_result = await self.db.execute(
                select(
                    ContractDocument.contract_id,
                    func.coalesce(func.sum(Payment.amount), 0),
                )
                .select_from(Payment)
                .join(ContractDocument, ContractDocument.document_id == Payment.document_id)
                .where(
                    ContractDocument.contract_id.in_(contract_ids),
                    Payment.is_voided == False,
                )
                .group_by(ContractDocument.contract_id)
            )
            paid_map = {row[0]: float(row[1]) for row in paid_result.all()}
            # 框架合同：通过项目关联计算已收金额
            fw_contract_ids_paid = [ct.id for ct in all_contracts if ct.contract_type == "框架合同"]
            if fw_contract_ids_paid:
                fw_paid_result = await self.db.execute(
                    select(
                        FrameworkContractProject.contract_id,
                        func.coalesce(func.sum(Payment.amount), 0),
                    )
                    .select_from(Payment)
                    .join(FCPD, FCPD.document_id == Payment.document_id)
                    .join(FrameworkContractProject, FCPD.project_id == FrameworkContractProject.id)
                    .where(
                        FrameworkContractProject.contract_id.in_(fw_contract_ids_paid),
                        Payment.is_voided == False,
                    )
                    .group_by(FrameworkContractProject.contract_id)
                )
                for row in fw_paid_result.all():
                    paid_map[row[0]] = paid_map.get(row[0], 0.0) + float(row[1])

        # Batch-fetch framework contract project totals (框架合同金额 = 子项目合计)
        from app.models.framework_contract import FrameworkContractProject
        fw_total_map: dict[UUID, float] = {}
        fw_contract_ids = [ct.id for ct in all_contracts if ct.contract_type == "框架合同"]
        if fw_contract_ids:
            fw_result = await self.db.execute(
                select(
                    FrameworkContractProject.contract_id,
                    func.coalesce(func.sum(FrameworkContractProject.project_amount), 0),
                )
                .where(
                    FrameworkContractProject.contract_id.in_(fw_contract_ids),
                    FrameworkContractProject.deleted_at.is_(None),
                )
                .group_by(FrameworkContractProject.contract_id)
            )
            fw_total_map = {row[0]: float(row[1]) for row in fw_result.all()}

        # Build response
        # 构建 document ID → 对象 映射（用于框架合同项目关联的单据查找）
        all_docs_by_id: dict[UUID, BusinessDocument] = {}
        for doc in all_orders + all_quotes:
            all_docs_by_id[doc.id] = doc

        debts = []
        for c in customers:
            customer_contracts = [ct for ct in all_contracts if ct.customer_id == c.id]
            customer_orders = [o for o in all_orders if o.customer_id == c.id]
            customer_quotes = [q for q in all_quotes if q.customer_id == c.id]

            # Separate standalone orders/quotes (not linked to any contract)
            standalone_orders = [o for o in customer_orders if o.id not in linked_doc_ids]
            standalone_quotes = [q for q in customer_quotes if q.id not in linked_doc_ids]

            # Skip customers with no contracts and no standalone orders/quotes
            if not customer_contracts and not standalone_orders and not standalone_quotes:
                continue

            # Stats from contracts (paid_amount from actual payments, not stored value)
            # 框架合同金额 = 子项目合计
            total_contract = 0.0
            for ct in customer_contracts:
                if ct.contract_type == "框架合同":
                    total_contract += fw_total_map.get(ct.id, 0.0)
                else:
                    total_contract += float(ct.total_amount)
            total_paid = sum(paid_map.get(ct.id, 0.0) for ct in customer_contracts)
            total_debt = max(0.0, total_contract - total_paid)
            lp = last_payments.get(c.id)

            def _ct_amount(ct):
                if ct.contract_type == "框架合同":
                    return fw_total_map.get(ct.id, 0.0)
                return float(ct.total_amount)

            # 获取某合同关联的单据（框架合同从项目关联获取，常规合同从 contract_documents 获取）
            def _get_ct_docs(ct, doc_type: str) -> list:
                if ct.contract_type == "框架合同":
                    dids = fw_doc_ids_by_contract.get(ct.id, set())
                    return [all_docs_by_id[did] for did in dids
                            if did in all_docs_by_id and all_docs_by_id[did].doc_type == doc_type]
                return [d for d in (ct.documents or []) if d.doc_type == doc_type]

            debts.append({
                "customer_id": str(c.id),
                "customer_name": c.name,
                "debt_amount": float(total_debt),
                "total_order_amount": float(total_contract),
                "total_paid": float(total_paid),
                "contract_count": len(customer_contracts),
                "order_count": len(standalone_orders),
                "quote_count": len(standalone_quotes),
                "last_payment_date": lp.isoformat() if lp else None,
                "contracts": [
                    {
                        "id": str(ct.id),
                        "contract_no": ct.contract_no,
                        "project_name": ct.project_name,
                        "total_amount": _ct_amount(ct),
                        "paid_amount": paid_map.get(ct.id, 0.0),
                        "unpaid_amount": max(0, _ct_amount(ct) - paid_map.get(ct.id, 0.0)),
                        "status": ct.status,
                        "contract_type": ct.contract_type,
                        "orders": [BusinessDocumentService._to_ref(d) for d in _get_ct_docs(ct, "order")],
                        "quotes": [BusinessDocumentService._to_ref(d) for d in _get_ct_docs(ct, "quote")],
                    }
                    for ct in customer_contracts
                ],
                "orders": [BusinessDocumentService._to_ref(o) for o in standalone_orders],
                "quotes": [BusinessDocumentService._to_ref(q) for q in standalone_quotes],
            })
        return debts

    async def _sum_orders(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(BusinessDocument.total_amount), 0))
            .where(and_(BusinessDocument.deleted_at.is_(None), BusinessDocument.created_at >= start, BusinessDocument.created_at <= end))
        )
        return result.scalar() or 0

    async def _sum_payments(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(and_(Payment.is_voided == False, Payment.created_at >= start, Payment.created_at <= end))
        )
        return result.scalar() or 0

    async def _calc_month_unpaid(self, start: datetime, end: datetime) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(BusinessDocument.unpaid_amount), 0))
            .where(and_(BusinessDocument.deleted_at.is_(None), BusinessDocument.created_at >= start, BusinessDocument.created_at <= end))
        )
        return result.scalar() or 0

    async def _count_tasks(self, model, statuses: list[str]) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(model).where(model.status.in_(statuses))
        )
        return result.scalar() or 0

    async def _count_overdue_orders(self) -> int:
        now = datetime.now()
        result = await self.db.execute(
            select(func.count()).select_from(BusinessDocument).where(
                and_(
                    BusinessDocument.deleted_at.is_(None),
                    BusinessDocument.status.in_(["confirmed", "in_progress", "in_production", "in_installation"]),
                    BusinessDocument.delivery_deadline < now,
                )
            )
        )
        return result.scalar() or 0

    async def _customer_debt_ranking(self, limit: int = 10) -> list:
        result = await self.db.execute(
            select(BusinessDocument.customer_id, func.sum(BusinessDocument.unpaid_amount).label("debt"))
            .where(BusinessDocument.deleted_at.is_(None), BusinessDocument.unpaid_amount > 0)
            .group_by(BusinessDocument.customer_id)
            .order_by(func.sum(BusinessDocument.unpaid_amount).desc())
            .limit(limit)
        )
        rows = result.all()
        ranking = []
        for customer_id, debt in rows:
            c_result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
            c = c_result.scalar_one_or_none()
            ranking.append({
                "customer_id": str(customer_id),
                "customer_name": c.name if c else "未知",
                "debt_amount": float(debt),
            })
        return ranking

    async def _list_orders_in_range(self, start: datetime, end: datetime) -> list[BusinessDocument]:
        result = await self.db.execute(
            select(BusinessDocument).where(
                and_(BusinessDocument.deleted_at.is_(None), BusinessDocument.created_at >= start, BusinessDocument.created_at <= end)
            ).order_by(BusinessDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def _list_payments_in_range(self, start: datetime, end: datetime) -> list[Payment]:
        result = await self.db.execute(
            select(Payment).where(
                and_(Payment.is_voided == False, Payment.created_at >= start, Payment.created_at <= end)
            ).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def _count_new_customers(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Customer).where(
                and_(Customer.deleted_at.is_(None), Customer.created_at >= start, Customer.created_at <= end)
            )
        )
        return result.scalar() or 0
