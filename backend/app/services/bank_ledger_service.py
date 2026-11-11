"""Account-level cash ledger assembled from ERP payments and manual movements."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select, text

from app.core.permissions import user_has_permission
from app.models.bank_ledger import BankLedgerEntry
from app.models.business_document import BusinessDocument
from app.models.company_account import CompanyAccount
from app.models.customer import Customer
from app.models.outsource import OutsourceVendor
from app.models.payment import Payment
from app.models.project_cost import ProjectCost
from app.services.expenditure_service import ExpenditureService

SUPPORTED_ACCOUNT_TYPES = {"bank", "wechat", "alipay"}
MONEY_ZERO = Decimal("0.00")


class BankLedgerService:
    def __init__(self, db, viewer):
        self.db = db
        self.viewer = viewer

    @staticmethod
    def _today():
        return datetime.now(ZoneInfo("Asia/Shanghai")).date()

    @staticmethod
    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    @staticmethod
    def _amount_value(value):
        return float(BankLedgerService._money(value))

    @staticmethod
    def audit_snapshot(entry):
        """Capture financial fields without copying counterparty account numbers."""
        return {
            "account_id": str(entry.account_id),
            "entry_type": entry.entry_type,
            "entry_date": entry.entry_date.isoformat(),
            "direction": entry.direction,
            "amount": BankLedgerService._amount_value(entry.amount),
            "summary": entry.summary,
            "counterparty_name": entry.counterparty_name,
            "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
            "category": entry.category,
            "project_name": entry.project_name,
            "department": entry.department,
            "order_id": str(entry.order_id) if entry.order_id else None,
        }

    async def _account(self, account_id, *, lock=False):
        query = select(CompanyAccount).where(CompanyAccount.id == account_id)
        if lock:
            query = query.with_for_update()
        account = await self.db.scalar(query)
        if account is None:
            raise ValueError("公司账户不存在")
        if account.account_type not in SUPPORTED_ACCOUNT_TYPES:
            raise ValueError("银行台账仅支持银行、微信和支付宝账户")
        return account

    @staticmethod
    def _opening_payload(entry):
        if entry is None:
            return None
        return {
            "entry_date": entry.entry_date.isoformat(),
            "amount": BankLedgerService._amount_value(entry.amount),
        }

    async def get_ledger(self, account_id: UUID, page=1, page_size=20):
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        await self._account(account_id)
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        opening_date = opening.entry_date if opening else None

        cash_payments = await ExpenditureService(self.db, self.viewer).list_account_cash_payments(
            account_id, start_date=opening_date,
        )
        receipts_query = (
            select(
                Payment.id, Payment.payment_no, Payment.document_id, Payment.paid_at,
                Payment.amount, Payment.remark, Customer.name.label("customer_name"),
                BusinessDocument.project_name, BusinessDocument.department,
            )
            .join(Customer, Customer.id == Payment.customer_id)
            .outerjoin(BusinessDocument, BusinessDocument.id == Payment.document_id)
            .where(
                Payment.payment_account_id == account_id,
                Payment.record_type == "receipt",
                Payment.is_voided.is_(False),
                Payment.paid_at.is_not(None),
            )
        )
        if opening_date:
            receipts_query = receipts_query.where(Payment.paid_at >= datetime.combine(opening_date, datetime.min.time()))
        receipts = (await self.db.execute(receipts_query)).mappings().all()
        manual_query = select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "manual",
        )
        if opening_date:
            manual_query = manual_query.where(BankLedgerEntry.entry_date >= opening_date)
        manual_entries = (await self.db.execute(
            manual_query.order_by(BankLedgerEntry.entry_date.asc(), BankLedgerEntry.created_at.asc())
        )).scalars().all()

        rows = []
        can_read_receipts = user_has_permission(self.viewer, "payment:read")
        for receipt in receipts:
            row_date = receipt["paid_at"].date()
            document_id = receipt["document_id"] if can_read_receipts else None
            rows.append({
                "id": "receipt:" + str(receipt["id"]),
                "entry_type": "source_receipt",
                "source_label": "客户收款",
                "source_kind": "receipt",
                "source_id": str(receipt["id"]) if can_read_receipts else None,
                "document_id": str(document_id) if document_id else None,
                "document_type": "order" if document_id else None,
                "entry_date": row_date.isoformat(),
                "summary": (receipt["remark"] or "") if can_read_receipts else "",
                "remark": None,
                "counterparty_account": None,
                "counterparty_name": receipt["customer_name"] if can_read_receipts else None,
                "category": "客户收款",
                "income_amount": self._money(receipt["amount"]),
                "expense_amount": MONEY_ZERO,
                "balance": None,
                "project_name": receipt["project_name"] if can_read_receipts else None,
                "department": receipt["department"] if can_read_receipts else None,
                "_sort": (row_date, 1, receipt["paid_at"].isoformat(), str(receipt["id"])),
            })
        for payment in cash_payments:
            paid_at = payment["paid_at"]
            row_date = paid_at.date()
            amount = self._money(payment["amount"])
            rows.append({
                "id": str(payment["row_key"]),
                "entry_type": "source_payment",
                "source_label": {
                    "expense": "费用付款",
                    "project_cost": "项目成本付款",
                    "outsource_task": "外协付款",
                    "outsource_payment": "外协付款",
                }.get(payment["source_kind"], "ERP付款"),
                "source_kind": payment["source_kind"],
                "source_id": str(payment["source_id"]),
                "document_id": str(payment["document_id"]) if payment["document_id"] else None,
                "document_type": payment["document_type"],
                "entry_date": row_date.isoformat(),
                "summary": payment.get("description") or "",
                "remark": payment.get("remark"),
                "counterparty_account": None,
                "counterparty_name": payment.get("supplier_name"),
                "category": payment.get("category"),
                "income_amount": MONEY_ZERO,
                "expense_amount": amount,
                "balance": None,
                "project_name": payment.get("project_name"),
                "department": payment.get("department"),
                "_sort": (row_date, 1, paid_at.isoformat(), str(payment["row_key"])),
            })
        for entry in manual_entries:
            amount = self._money(entry.amount)
            is_income = entry.direction == "income"
            rows.append({
                "id": str(entry.id),
                "entry_type": "manual",
                "source_label": "手工登记",
                "entry_date": entry.entry_date.isoformat(),
                "summary": entry.summary,
                "remark": None,
                "counterparty_account": entry.counterparty_account,
                "counterparty_name": entry.counterparty_name,
                "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
                "category": entry.category,
                "income_amount": amount if is_income else MONEY_ZERO,
                "expense_amount": MONEY_ZERO if is_income else amount,
                "balance": None,
                "project_name": entry.project_name,
                "department": entry.department,
                "order_id": str(entry.order_id) if entry.order_id else None,
                "_sort": (
                    entry.entry_date,
                    2,
                    entry.created_at.isoformat() if entry.created_at else "",
                    str(entry.id),
                ),
            })

        opening_amount = self._money(opening.amount) if opening else None
        if opening:
            rows.append({
                "id": "opening:" + str(opening.id),
                "entry_type": "opening_balance",
                "source_label": "期初",
                "entry_date": opening.entry_date.isoformat(),
                "summary": "",
                "remark": None,
                "counterparty_account": None,
                "counterparty_name": None,
                "category": "期初余额",
                "income_amount": MONEY_ZERO,
                "expense_amount": MONEY_ZERO,
                "balance": opening_amount,
                "project_name": None,
                "department": None,
                "_sort": (opening.entry_date, 0, "", str(opening.id)),
            })

        def daily_balance_order(row):
            if row["entry_type"] == "opening_balance":
                flow_order = 0
            elif self._money(row["income_amount"]) > MONEY_ZERO:
                flow_order = 1
            else:
                flow_order = 2
            return flow_order, row["_sort"][2], row["_sort"][3]

        rows.sort(key=lambda row: (row["entry_date"], *daily_balance_order(row)))
        balance = opening_amount
        income_total = MONEY_ZERO
        expense_total = MONEY_ZERO
        daily_totals = {}
        monthly_totals = {}
        yearly_totals = {}
        transaction_count = 0
        for row in rows:
            if row["entry_type"] == "opening_balance":
                row["balance"] = balance
            else:
                transaction_count += 1
                income = self._money(row["income_amount"])
                expense = self._money(row["expense_amount"])
                income_total += income
                expense_total += expense
                daily_total = daily_totals.setdefault(row["entry_date"], {
                    "income_amount": MONEY_ZERO,
                    "expense_amount": MONEY_ZERO,
                    "balance": None,
                })
                month_key = row["entry_date"][:7]
                month_total = monthly_totals.setdefault(month_key, {
                    "income_amount": MONEY_ZERO,
                    "expense_amount": MONEY_ZERO,
                    "balance": None,
                })
                year_key = row["entry_date"][:4]
                year_total = yearly_totals.setdefault(year_key, {
                    "income_amount": MONEY_ZERO,
                    "expense_amount": MONEY_ZERO,
                    "balance": None,
                })
                month_total["income_amount"] += income
                month_total["expense_amount"] += expense
                year_total["income_amount"] += income
                year_total["expense_amount"] += expense
                daily_total["income_amount"] += income
                daily_total["expense_amount"] += expense
                if balance is not None:
                    balance += income - expense
                    row["balance"] = balance
                daily_total["balance"] = balance
                month_total["balance"] = balance
                year_total["balance"] = balance
            row["income_amount"] = self._amount_value(row["income_amount"])
            row["expense_amount"] = self._amount_value(row["expense_amount"])
            row["balance"] = self._amount_value(row["balance"]) if row["balance"] is not None else None

        display_rows = []
        rows_by_date = {}
        for row in rows:
            rows_by_date.setdefault(row["entry_date"], []).append(row)
        for year_key in sorted({row_date[:4] for row_date in rows_by_date}, reverse=True):
            year_total = yearly_totals.get(year_key)
            if year_total is not None:
                display_rows.append({
                    "id": f"yearly-total:{year_key}",
                    "entry_type": "yearly_total",
                    "source_label": "本年合计",
                    "year_label": f"{year_key}年",
                    "entry_date": f"{year_key}-01-01",
                    "summary": "",
                    "remark": None,
                    "counterparty_account": None,
                    "counterparty_name": None,
                    "category": None,
                    "income_amount": self._amount_value(year_total["income_amount"]),
                    "expense_amount": self._amount_value(year_total["expense_amount"]),
                    "balance": self._amount_value(year_total["balance"]) if year_total["balance"] is not None else None,
                    "project_name": None,
                    "department": None,
                })
            month_keys = sorted(
                {row_date[:7] for row_date in rows_by_date if row_date.startswith(year_key)},
                reverse=True,
            )
            for month_key in month_keys:
                month_total = monthly_totals.get(month_key)
                if month_total is not None:
                    year, month = month_key.split("-")
                    display_rows.append({
                        "id": f"monthly-total:{month_key}",
                        "entry_type": "monthly_total",
                        "source_label": "本月合计",
                        "month_label": f"{year}年{int(month)}月",
                        "entry_date": f"{month_key}-01",
                        "summary": "",
                        "remark": None,
                        "counterparty_account": None,
                        "counterparty_name": None,
                        "category": None,
                        "income_amount": self._amount_value(month_total["income_amount"]),
                        "expense_amount": self._amount_value(month_total["expense_amount"]),
                        "balance": self._amount_value(month_total["balance"]) if month_total["balance"] is not None else None,
                        "project_name": None,
                        "department": None,
                    })
                month_dates = sorted(
                    (row_date for row_date in rows_by_date if row_date.startswith(month_key)),
                    reverse=True,
                )
                for row_date in month_dates:
                    day_rows = sorted(rows_by_date[row_date], key=daily_balance_order)
                    display_rows.extend(day_rows)
                    daily_total = daily_totals.get(row_date)
                    if daily_total is not None and daily_total["balance"] is not None:
                        display_rows.append({
                            "id": f"daily-balance:{row_date}",
                            "entry_type": "daily_balance",
                            "source_label": "当日余额",
                            "entry_date": row_date,
                            "summary": "",
                            "remark": None,
                            "counterparty_account": None,
                            "counterparty_name": None,
                            "category": None,
                            "income_amount": MONEY_ZERO,
                            "expense_amount": MONEY_ZERO,
                            "balance": self._amount_value(daily_total["balance"]),
                            "project_name": None,
                            "department": None,
                        })
        rows = display_rows
        for row in rows:
            row.pop("_sort", None)
        total = len(rows)
        start = (page - 1) * page_size
        page_rows = rows[start:start + page_size]
        return {
            "items": page_rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "opening_balance": self._opening_payload(opening),
            "summary": {
                "opening_balance": self._amount_value(opening_amount) if opening_amount is not None else None,
                "income_amount": self._amount_value(income_total),
                "expense_amount": self._amount_value(expense_total),
                "balance": self._amount_value(balance) if balance is not None else None,
                "transaction_count": transaction_count,
            },
        }

    async def set_opening_balance(self, account_id: UUID, data: dict, created_by: UUID):
        account = await self._account(account_id, lock=True)
        entry_date = data["entry_date"]
        amount = self._money(data["amount"])
        if entry_date > self._today():
            raise ValueError("期初日期不能晚于今天")
        manual_before_opening = await self.db.scalar(select(exists().where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "manual",
            BankLedgerEntry.entry_date < entry_date,
        )))
        if manual_before_opening:
            raise ValueError("期初日期不能晚于已登记的手工流水日期")
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "opening_balance",
        ).with_for_update())
        before = {
            "entry_date": opening.entry_date.isoformat(),
            "amount": self._amount_value(opening.amount),
        } if opening else None
        if opening is None:
            opening = BankLedgerEntry(
                account_id=account.id,
                entry_type="opening_balance",
                direction="opening",
                entry_date=entry_date,
                amount=amount,
                summary="期初余额",
                created_by=created_by,
            )
            self.db.add(opening)
        else:
            opening.entry_date = entry_date
            opening.amount = amount
        await self.db.flush()
        return opening, before

    async def create_entry(self, account_id: UUID, data: dict, created_by: UUID):
        request_id = data["request_id"]
        await self._lock_business_request(request_id)
        account = await self._account(account_id, lock=True)
        await self._assert_request_unclaimed(request_id, Payment, ProjectCost)
        existing = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.request_id == request_id,
        ).with_for_update())
        if existing:
            if existing.account_id != account_id:
                raise ValueError("该流水请求编号已被另一账户使用")
            return existing, False
        if not account.is_active:
            raise ValueError("已停用账户不能登记新流水")
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account.id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        if opening is None:
            raise ValueError("请先设置该账户的期初余额")
        entry_date = data["entry_date"]
        if entry_date > self._today():
            raise ValueError("流水日期不能晚于今天")
        if entry_date < opening.entry_date:
            raise ValueError("流水日期不能早于期初日期")

        values = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in data.items()
        }
        for key in ("counterparty_account", "counterparty_name", "category", "project_name", "department"):
            if values.get(key) == "":
                values[key] = None
        supplier_id = values.get("counterparty_supplier_id")
        if supplier_id:
            supplier = await self.db.scalar(select(OutsourceVendor).where(
                OutsourceVendor.id == supplier_id,
                OutsourceVendor.deleted_at.is_(None),
                OutsourceVendor.is_active.is_(True),
            ))
            if supplier is None:
                raise ValueError("供应商不存在或已停用，请重新选择")
            values["counterparty_name"] = supplier.name

        order_id = values.get("order_id")
        if order_id:
            order = await self.db.scalar(select(BusinessDocument).where(
                BusinessDocument.id == order_id,
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
            ))
            if order is None:
                raise ValueError("订单不存在或已删除，请重新选择")
            values["project_name"] = order.project_name
            values["department"] = order.department

        entry = BankLedgerEntry(
            account_id=account.id,
            entry_type="manual",
            direction=values["direction"],
            entry_date=entry_date,
            amount=self._money(values["amount"]),
            summary=values["summary"],
            counterparty_account=values.get("counterparty_account"),
            counterparty_name=values.get("counterparty_name"),
            counterparty_supplier_id=supplier_id,
            category=values.get("category"),
            project_name=values.get("project_name"),
            department=values.get("department"),
            order_id=order_id,
            request_id=request_id,
            created_by=created_by,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry, True

    async def update_entry(self, account_id: UUID, entry_id: UUID, data: dict):
        await self._account(account_id, lock=True)
        entry = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.id == entry_id,
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "manual",
        ).with_for_update())
        if entry is None:
            raise ValueError("手工台账流水不存在或不可编辑")

        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        if opening is None:
            raise ValueError("账户期初余额不存在，不能编辑手工流水")

        values = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in data.items()
        }
        for key in (
            "counterparty_account", "counterparty_name", "category",
            "project_name", "department",
        ):
            if values.get(key) == "":
                values[key] = None

        entry_date = values["entry_date"]
        if entry_date > self._today():
            raise ValueError("流水日期不能晚于今天")
        if entry_date < opening.entry_date:
            raise ValueError("流水日期不能早于期初日期")

        supplier_id = values.get("counterparty_supplier_id")
        if supplier_id:
            supplier = await self.db.scalar(select(OutsourceVendor).where(
                OutsourceVendor.id == supplier_id,
                OutsourceVendor.deleted_at.is_(None),
                OutsourceVendor.is_active.is_(True),
            ))
            if supplier is None:
                if supplier_id != entry.counterparty_supplier_id:
                    raise ValueError("供应商不存在或已停用，请重新选择")
                values["counterparty_name"] = entry.counterparty_name
            else:
                values["counterparty_name"] = supplier.name

        order_id = values.get("order_id")
        if order_id:
            if order_id == entry.order_id:
                order = await self.db.scalar(select(BusinessDocument).where(
                    BusinessDocument.id == order_id,
                    BusinessDocument.doc_type == "order",
                ))
            else:
                order = await self.db.scalar(select(BusinessDocument).where(
                    BusinessDocument.id == order_id,
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.deleted_at.is_(None),
                ))
            if order is None:
                raise ValueError("订单不存在或已删除，请重新选择")
            values["project_name"] = order.project_name
            values["department"] = order.department

        before = self.audit_snapshot(entry)
        entry.entry_date = entry_date
        entry.direction = values["direction"]
        entry.amount = self._money(values["amount"])
        entry.summary = values["summary"]
        entry.counterparty_account = values.get("counterparty_account")
        entry.counterparty_name = values.get("counterparty_name")
        entry.counterparty_supplier_id = supplier_id
        entry.category = values.get("category")
        entry.project_name = values.get("project_name")
        entry.department = values.get("department")
        entry.order_id = order_id
        await self.db.flush()
        return entry, before

    async def delete_entry(self, account_id: UUID, entry_id: UUID):
        await self._account(account_id, lock=True)
        entry = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.id == entry_id,
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "manual",
        ).with_for_update())
        if entry is None:
            raise ValueError("手工台账流水不存在或不可删除")
        before = self.audit_snapshot(entry)
        await self.db.delete(entry)
        await self.db.flush()
        return before

    async def _lock_business_request(self, request_id: UUID):
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "bank-business-request:" + str(request_id)},
        )

    async def _business_account(self, account_id: UUID, entry_date: date):
        account = await self._account(account_id, lock=True)
        if not account.is_active:
            raise ValueError("已停用账户不能登记新流水")
        opening = await self.db.scalar(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id == account_id,
            BankLedgerEntry.entry_type == "opening_balance",
        ))
        if opening is None:
            raise ValueError("请先设置该账户的期初余额")
        if entry_date > self._today() or entry_date < opening.entry_date:
            raise ValueError("流水日期须在期初日期与今天之间")
        return account

    @staticmethod
    def _payment_method(account):
        return {"bank": "转账支付", "wechat": "微信支付", "alipay": "支付宝转账"}[account.account_type]

    @classmethod
    def _same_business_movement(cls, record, account_id, movement_date, data):
        return (
            record.payment_account_id == account_id
            and record.document_id == data["order_id"]
            and cls._money(record.amount) == data["amount"]
            and movement_date is not None
            and movement_date.date() == data["entry_date"]
        )

    async def _assert_request_unclaimed(self, request_id: UUID, *models):
        for model in models:
            existing_id = await self.db.scalar(select(model.id).where(model.request_id == request_id))
            if existing_id is not None:
                raise ValueError("该请求编号已用于其他类型的业务登记")

    async def create_project_cost(self, account_id: UUID, data: dict, created_by: UUID):
        from app.services.project_cost_service import ProjectCostService

        await self._lock_business_request(data["request_id"])
        existing = await self.db.scalar(select(ProjectCost).where(ProjectCost.request_id == data["request_id"]))
        if existing:
            if not self._same_business_movement(existing, account_id, existing.cost_date, data):
                raise ValueError("该请求编号已用于另一笔项目成本")
            return {"id": str(existing.id), "cost_no": existing.cost_no}, False
        await self._assert_request_unclaimed(data["request_id"], Payment, BankLedgerEntry)
        account = await self._business_account(account_id, data["entry_date"])
        order_id = await self.db.scalar(select(BusinessDocument.id).where(
            BusinessDocument.id == data["order_id"],
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        ).with_for_update())
        if order_id is None:
            raise ValueError("请选择有效订单")
        cost = await ProjectCostService(self.db).create_cost({
            "request_id": data["request_id"],
            "order_id": str(order_id),
            "amount": data["amount"],
            "debt_amount": 0,
            "category": data["category"],
            "summary": data["summary"],
            "cost_date": data["entry_date"].isoformat(),
            "payment_account_id": str(account_id),
            "payment_method": self._payment_method(account),
            "supplier_id": str(data["supplier_id"]) if data.get("supplier_id") else None,
            "payee_company_name": data.get("counterparty_name") or None,
        }, created_by)
        return cost, True

    async def create_customer_receipt(self, account_id: UUID, data: dict, created_by: UUID):
        from app.services.payment_service import PaymentService

        await self._lock_business_request(data["request_id"])
        existing = await self.db.scalar(select(Payment).where(Payment.request_id == data["request_id"]))
        if existing:
            if not self._same_business_movement(existing, account_id, existing.paid_at, data):
                raise ValueError("该请求编号已用于另一笔客户收款")
            return {"id": str(existing.id), "payment_no": existing.payment_no}, False
        await self._assert_request_unclaimed(data["request_id"], ProjectCost, BankLedgerEntry)
        account = await self._business_account(account_id, data["entry_date"])
        customer_id = await self.db.scalar(select(BusinessDocument.customer_id).where(
            BusinessDocument.id == data["order_id"],
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        ))
        if not customer_id:
            raise ValueError("请选择已关联客户的有效订单")
        receipt = await PaymentService(self.db).create_payment({
            "request_id": data["request_id"],
            "order_id": str(data["order_id"]),
            "customer_id": str(customer_id),
            "amount": data["amount"],
            "payment_account_id": str(account_id),
            "payment_method": self._payment_method(account),
            "paid_at": data["entry_date"].isoformat(),
            "remark": data["summary"],
        }, created_by, allow_standalone=True)
        return receipt, True

    @staticmethod
    def entry_payload(entry):
        return {
            "id": str(entry.id),
            "account_id": str(entry.account_id),
            "entry_type": entry.entry_type,
            "direction": entry.direction,
            "entry_date": entry.entry_date.isoformat(),
            "amount": BankLedgerService._amount_value(entry.amount),
            "summary": entry.summary,
            "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
            "order_id": str(entry.order_id) if entry.order_id else None,
        }
