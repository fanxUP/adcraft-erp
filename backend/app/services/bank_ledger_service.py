"""Account-level cash ledger assembled from ERP payments and manual movements."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select, text
from sqlalchemy.orm import selectinload

from app.core.permissions import user_has_permission
from app.models.bank_ledger import BankLedgerEntry
from app.models.business_document import BusinessDocument
from app.models.company_account import CompanyAccount
from app.models.customer import Customer
from app.models.outsource import OutsourceVendor
from app.models.payment import Payment
from app.models.project_cost import ProjectCost
from app.services.expenditure_service import ExpenditureService
from app.services.finance_category_service import FinanceCategoryService

SUPPORTED_ACCOUNT_TYPES = {"bank", "wechat", "alipay", "cash", "other"}
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
            raise ValueError("银行台账账户类型无效")
        return account

    @staticmethod
    def _opening_payload(entry):
        if entry is None:
            return None
        return {
            "entry_date": entry.entry_date.isoformat(),
            "amount": BankLedgerService._amount_value(entry.amount),
        }

    @staticmethod
    def _filters_active(filters):
        return any(value not in (None, "") for value in (filters or {}).values())

    @staticmethod
    def _normalize_filters(filters):
        normalized = dict(filters or {})
        for key in ("keyword", "category"):
            if normalized.get(key) is not None:
                normalized[key] = normalized[key].strip() or None
        start_date, end_date = normalized.get("start_date"), normalized.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")
        amount_min, amount_max = normalized.get("amount_min"), normalized.get("amount_max")
        if amount_min is not None and amount_max is not None and amount_min > amount_max:
            raise ValueError("最低金额不能大于最高金额")
        if normalized.get("direction") not in (None, "income", "expense"):
            raise ValueError("收支方向无效")
        return {key: value for key, value in normalized.items() if value not in (None, "")}

    @staticmethod
    def _daily_display_order(row):
        if row.get("_category_code") == "bank_fee" or (row.get("category") or "").strip() == "手续费":
            flow_order = 0
        elif BankLedgerService._money(row["expense_amount"]) > MONEY_ZERO:
            flow_order = 1
        elif BankLedgerService._money(row["income_amount"]) > MONEY_ZERO:
            flow_order = 2
        elif row["entry_type"] == "opening_balance":
            flow_order = 3
        else:
            flow_order = 4
        return flow_order, row["_sort"][2], row["_sort"][3]

    @classmethod
    def _calculation_order(cls, rows):
        rows_by_date = {}
        for row in rows:
            rows_by_date.setdefault(row["entry_date"], []).append(row)
        ordered = []
        for row_date in sorted(rows_by_date):
            day_rows = sorted(rows_by_date[row_date], key=cls._daily_display_order)
            ordered.extend(reversed(day_rows))
        return ordered

    @classmethod
    def _detail_display_order(cls, rows):
        rows_by_date = {}
        for row in rows:
            rows_by_date.setdefault(row["entry_date"], []).append(row)
        ordered = []
        for row_date in sorted(rows_by_date, reverse=True):
            ordered.extend(sorted(rows_by_date[row_date], key=cls._daily_display_order))
        return ordered

    @classmethod
    def _calculate_account_rows(cls, rows, opening):
        opening_amount = cls._money(opening.amount) if opening else None
        rows = cls._calculation_order(rows)
        balance = opening_amount
        income_total = MONEY_ZERO
        expense_total = MONEY_ZERO
        monthly_totals = {}
        yearly_totals = {}
        transaction_count = 0
        for row in rows:
            if row["entry_type"] == "opening_balance":
                row["balance"] = balance
            else:
                transaction_count += 1
                income = cls._money(row["income_amount"])
                expense = cls._money(row["expense_amount"])
                income_total += income
                expense_total += expense
                month_key = row["entry_date"][:7]
                month_total = monthly_totals.setdefault(month_key, {
                    "income_amount": MONEY_ZERO, "expense_amount": MONEY_ZERO, "balance": None,
                })
                year_key = row["entry_date"][:4]
                year_total = yearly_totals.setdefault(year_key, {
                    "income_amount": MONEY_ZERO, "expense_amount": MONEY_ZERO, "balance": None,
                })
                month_total["income_amount"] += income
                month_total["expense_amount"] += expense
                year_total["income_amount"] += income
                year_total["expense_amount"] += expense
                if balance is not None:
                    balance += income - expense
                    row["balance"] = balance
                month_total["balance"] = balance
                year_total["balance"] = balance
            row["income_amount"] = cls._amount_value(row["income_amount"])
            row["expense_amount"] = cls._amount_value(row["expense_amount"])
            row["balance"] = cls._amount_value(row["balance"]) if row["balance"] is not None else None
        return rows, {
            "opening_amount": opening_amount,
            "income_amount": income_total,
            "expense_amount": expense_total,
            "balance": balance,
            "transaction_count": transaction_count,
            "monthly_totals": monthly_totals,
            "yearly_totals": yearly_totals,
        }

    @classmethod
    def _period_display_rows(cls, rows, totals):
        rows_by_date = {}
        for row in rows:
            rows_by_date.setdefault(row["entry_date"], []).append(row)
        display_rows = []
        for year_key in sorted({row_date[:4] for row_date in rows_by_date}, reverse=True):
            year_total = totals["yearly_totals"].get(year_key)
            if year_total is not None:
                display_rows.append({
                    "id": f"yearly-total:{year_key}", "entry_type": "yearly_total",
                    "source_label": "本年合计", "year_label": f"{year_key}年",
                    "entry_date": f"{year_key}-01-01", "summary": "", "remark": None,
                    "counterparty_account": None, "counterparty_name": None, "category": None,
                    "income_amount": cls._amount_value(year_total["income_amount"]),
                    "expense_amount": cls._amount_value(year_total["expense_amount"]),
                    "balance": cls._amount_value(year_total["balance"]) if year_total["balance"] is not None else None,
                    "project_name": None, "department": None,
                })
            month_keys = sorted(
                {row_date[:7] for row_date in rows_by_date if row_date.startswith(year_key)}, reverse=True,
            )
            for month_key in month_keys:
                month_total = totals["monthly_totals"].get(month_key)
                if month_total is not None:
                    year, month = month_key.split("-")
                    display_rows.append({
                        "id": f"monthly-total:{month_key}", "entry_type": "monthly_total",
                        "source_label": "本月合计", "month_label": f"{year}年{int(month)}月",
                        "entry_date": f"{month_key}-01", "summary": "", "remark": None,
                        "counterparty_account": None, "counterparty_name": None, "category": None,
                        "income_amount": cls._amount_value(month_total["income_amount"]),
                        "expense_amount": cls._amount_value(month_total["expense_amount"]),
                        "balance": cls._amount_value(month_total["balance"]) if month_total["balance"] is not None else None,
                        "project_name": None, "department": None,
                    })
                month_dates = sorted(
                    (row_date for row_date in rows_by_date if row_date.startswith(month_key)), reverse=True,
                )
                for row_date in month_dates:
                    display_rows.extend(sorted(rows_by_date[row_date], key=cls._daily_display_order))
        return display_rows

    @classmethod
    def _filter_rows(cls, rows, filters, *, account=None):
        if not filters:
            return list(rows)
        keyword = (filters.get("keyword") or "").casefold()
        start_date, end_date = filters.get("start_date"), filters.get("end_date")
        category = (filters.get("category") or "").casefold()
        direction = filters.get("direction")
        amount_min, amount_max = filters.get("amount_min"), filters.get("amount_max")
        account_text = ""
        if account is not None:
            account_text = f"{account.name} {cls._account_label(account)}".casefold()
        matched = []
        for row in rows:
            if start_date and row["entry_date"] < start_date.isoformat():
                continue
            if end_date and row["entry_date"] > end_date.isoformat():
                continue
            if category and (row.get("category") or "").casefold() != category:
                continue
            income = cls._money(row["income_amount"])
            expense = cls._money(row["expense_amount"])
            if direction == "income" and income <= MONEY_ZERO:
                continue
            if direction == "expense" and expense <= MONEY_ZERO:
                continue
            amount = income + expense
            if amount_min is not None and amount < amount_min:
                continue
            if amount_max is not None and amount > amount_max:
                continue
            if keyword:
                searchable = " ".join(str(row.get(key) or "") for key in (
                    "counterparty_name", "category", "summary", "remark", "project_name", "department",
                )) + " " + account_text
                if keyword not in searchable.casefold():
                    continue
            matched.append(row)
        return matched

    @classmethod
    def _matched_summary(cls, rows, *, account_count=None):
        return {
            "matching_count": len(rows),
            "income_amount": cls._amount_value(sum((cls._money(row["income_amount"]) for row in rows), MONEY_ZERO)),
            "expense_amount": cls._amount_value(sum((cls._money(row["expense_amount"]) for row in rows), MONEY_ZERO)),
            **({"account_count": account_count} if account_count is not None else {}),
        }

    @staticmethod
    def _account_label(account):
        number = account.account_number
        tail = number[-4:] if number and len(number) > 4 else None
        label = account.name + (f"（尾号 {tail}）" if tail else "（账号已隐藏）" if number else "")
        type_labels = {"wechat": "微信", "alipay": "支付宝", "cash": "现金", "other": "其他"}
        return f"{type_labels[account.account_type]} · {label}" if account.account_type != "bank" else label

    async def _load_account_rows(self, accounts):
        account_ids = [account.id for account in accounts]
        rows_by_account = {account_id: [] for account_id in account_ids}
        if not account_ids:
            return {}, rows_by_account

        openings = (await self.db.execute(select(BankLedgerEntry).where(
            BankLedgerEntry.account_id.in_(account_ids),
            BankLedgerEntry.entry_type == "opening_balance",
        ))).scalars().all()
        openings_by_account = {opening.account_id: opening for opening in openings}
        opening_dates = {account_id: opening.entry_date for account_id, opening in openings_by_account.items()}

        expenditure_service = ExpenditureService(self.db, self.viewer)
        if len(accounts) == 1:
            account_id = account_ids[0]
            cash_payments = await expenditure_service.list_account_cash_payments(
                account_id, start_date=opening_dates.get(account_id),
            )
        else:
            cash_payments = await expenditure_service.list_account_cash_payments_for_accounts(account_ids)
        receipts_query = (
            select(
                Payment.id, Payment.payment_account_id, Payment.payment_no, Payment.document_id, Payment.paid_at,
                Payment.amount, Payment.remark, Customer.name.label("customer_name"),
                BusinessDocument.project_name, BusinessDocument.department,
            )
            .join(Customer, Customer.id == Payment.customer_id)
            .outerjoin(BusinessDocument, BusinessDocument.id == Payment.document_id)
            .where(
                Payment.payment_account_id.in_(account_ids),
                Payment.record_type == "receipt",
                Payment.is_voided.is_(False),
                Payment.paid_at.is_not(None),
            )
        )
        if len(accounts) == 1:
            opening_date = opening_dates.get(account_ids[0])
            if opening_date:
                receipts_query = receipts_query.where(
                    Payment.paid_at >= datetime.combine(opening_date, datetime.min.time()),
                )
        receipts = (await self.db.execute(receipts_query)).mappings().all()
        manual_query = select(BankLedgerEntry).where(
            BankLedgerEntry.account_id.in_(account_ids),
            BankLedgerEntry.entry_type == "manual",
        ).options(selectinload(BankLedgerEntry.category_record))
        if len(accounts) == 1:
            opening_date = opening_dates.get(account_ids[0])
            if opening_date:
                manual_query = manual_query.where(BankLedgerEntry.entry_date >= opening_date)
        manual_entries = (await self.db.execute(
            manual_query.order_by(BankLedgerEntry.account_id, BankLedgerEntry.entry_date, BankLedgerEntry.created_at)
        )).scalars().all()

        can_read_receipts = user_has_permission(self.viewer, "payment:read")
        for receipt in receipts:
            account_id = receipt["payment_account_id"]
            paid_at = receipt["paid_at"]
            opening_date = opening_dates.get(account_id)
            if opening_date and paid_at < datetime.combine(opening_date, datetime.min.time()):
                continue
            row_date = paid_at.date()
            document_id = receipt["document_id"] if can_read_receipts else None
            rows_by_account[account_id].append({
                "id": "receipt:" + str(receipt["id"]), "entry_type": "source_receipt",
                "source_label": "客户收款", "source_kind": "receipt",
                "source_id": str(receipt["id"]) if can_read_receipts else None,
                "document_id": str(document_id) if document_id else None,
                "document_type": "order" if document_id else None,
                "entry_date": row_date.isoformat(),
                "summary": (receipt["remark"] or "") if can_read_receipts else "",
                "remark": None, "counterparty_account": None,
                "counterparty_name": receipt["customer_name"] if can_read_receipts else None,
                "category": "客户收款", "income_amount": self._money(receipt["amount"]),
                "expense_amount": MONEY_ZERO, "balance": None,
                "project_name": receipt["project_name"] if can_read_receipts else None,
                "department": receipt["department"] if can_read_receipts else None,
                "_sort": (row_date, 1, paid_at.isoformat(), str(receipt["id"])),
            })

        for payment in cash_payments:
            account_id = payment["payment_account_id"]
            paid_at = payment["paid_at"]
            opening_date = opening_dates.get(account_id)
            if opening_date and paid_at < datetime.combine(opening_date, datetime.min.time()):
                continue
            row_date = paid_at.date()
            rows_by_account[account_id].append({
                "id": str(payment["row_key"]), "entry_type": "source_payment",
                "source_label": {
                    "expense": "费用付款", "project_cost": "项目成本付款",
                    "outsource_task": "外协付款", "outsource_payment": "外协付款",
                }.get(payment["source_kind"], "ERP付款"),
                "source_kind": payment["source_kind"], "source_id": str(payment["source_id"]),
                "document_id": str(payment["document_id"]) if payment["document_id"] else None,
                "document_type": payment["document_type"], "entry_date": row_date.isoformat(),
                "summary": payment.get("description") or "", "remark": payment.get("remark"),
                "counterparty_account": None, "counterparty_name": payment.get("supplier_name"),
                "category": payment.get("category"), "_category_code": payment.get("category_code"),
                "income_amount": MONEY_ZERO, "expense_amount": self._money(payment["amount"]),
                "balance": None, "project_name": payment.get("project_name"),
                "department": payment.get("department"),
                "_sort": (row_date, 1, paid_at.isoformat(), str(payment["row_key"])),
            })

        for entry in manual_entries:
            opening_date = opening_dates.get(entry.account_id)
            if opening_date and entry.entry_date < opening_date:
                continue
            amount = self._money(entry.amount)
            is_income = entry.direction == "income"
            rows_by_account[entry.account_id].append({
                "id": str(entry.id), "entry_type": "manual", "source_label": "手工登记",
                "entry_date": entry.entry_date.isoformat(), "summary": entry.summary,
                "remark": None, "counterparty_account": entry.counterparty_account,
                "counterparty_name": entry.counterparty_name,
                "counterparty_supplier_id": str(entry.counterparty_supplier_id) if entry.counterparty_supplier_id else None,
                "category": entry.category, "_category_code": entry.category_record.code if entry.category_record else None,
                "income_amount": amount if is_income else MONEY_ZERO,
                "expense_amount": MONEY_ZERO if is_income else amount, "balance": None,
                "project_name": entry.project_name, "department": entry.department,
                "order_id": str(entry.order_id) if entry.order_id else None,
                "_sort": (entry.entry_date, 2, entry.created_at.isoformat() if entry.created_at else "", str(entry.id)),
            })

        for account_id, opening in openings_by_account.items():
            opening_amount = self._money(opening.amount)
            rows_by_account[account_id].append({
                "id": "opening:" + str(opening.id), "entry_type": "opening_balance",
                "source_label": "期初", "entry_date": opening.entry_date.isoformat(),
                "summary": "", "remark": None, "counterparty_account": None,
                "counterparty_name": None, "category": "期初余额",
                "income_amount": MONEY_ZERO, "expense_amount": MONEY_ZERO,
                "balance": opening_amount, "project_name": None, "department": None,
                "_sort": (opening.entry_date, 0, "", str(opening.id)),
            })
        return openings_by_account, rows_by_account

    async def _account_ledger_data(self, account):
        openings, rows_by_account = await self._load_account_rows([account])
        opening = openings.get(account.id)
        rows, totals = self._calculate_account_rows(rows_by_account[account.id], opening)
        return opening, rows, totals

    async def get_ledger(self, account_id: UUID, page=1, page_size=20, *, filters=None):
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        filters = self._normalize_filters(filters)
        account = await self._account(account_id)
        opening, rows, totals = await self._account_ledger_data(account)
        if self._filters_active(filters):
            rows = self._detail_display_order(self._filter_rows(rows, filters, account=account))
            matched_summary = self._matched_summary(rows)
        else:
            rows = self._period_display_rows(rows, totals)
            matched_summary = None
        total = len(rows)
        page_rows = rows[(page - 1) * page_size:page * page_size]
        for row in page_rows:
            row.pop("_sort", None)
            row.pop("_category_code", None)
        result = {
            "items": page_rows, "total": total, "page": page, "page_size": page_size,
            "opening_balance": self._opening_payload(opening),
            "summary": {
                "opening_balance": self._amount_value(totals["opening_amount"]) if totals["opening_amount"] is not None else None,
                "income_amount": self._amount_value(totals["income_amount"]),
                "expense_amount": self._amount_value(totals["expense_amount"]),
                "balance": self._amount_value(totals["balance"]) if totals["balance"] is not None else None,
                "transaction_count": totals["transaction_count"],
            },
        }
        if matched_summary is not None:
            result["matched_summary"] = matched_summary
        return result

    async def search_ledgers(self, page=1, page_size=20, *, filters=None, account_id=None):
        if page < 1 or not 1 <= page_size <= 200:
            raise ValueError("列表参数无效")
        filters = self._normalize_filters(filters)
        query = select(CompanyAccount).where(CompanyAccount.account_type.in_(SUPPORTED_ACCOUNT_TYPES))
        if account_id is not None:
            query = query.where(CompanyAccount.id == account_id)
        accounts = (await self.db.execute(query.order_by(CompanyAccount.name))).scalars().all()
        if account_id is not None and not accounts:
            await self._account(account_id)
            raise ValueError("公司账户不存在")

        openings, rows_by_account = await self._load_account_rows(accounts)
        matched_rows = []
        matched_income = MONEY_ZERO
        matched_expense = MONEY_ZERO
        matched_accounts = set()
        for account in accounts:
            rows, _totals = self._calculate_account_rows(
                rows_by_account[account.id], openings.get(account.id),
            )
            rows = self._detail_display_order(self._filter_rows(rows, filters, account=account))
            if rows:
                matched_accounts.add(account.id)
            label = self._account_label(account)
            for row in rows:
                matched_income += self._money(row["income_amount"])
                matched_expense += self._money(row["expense_amount"])
                row["account_id"] = str(account.id)
                row["account_name"] = account.name
                row["account_label"] = label
                row["account_is_active"] = account.is_active
                row["counterparty_account"] = None
                matched_rows.append(row)

        # Stable sorting keeps each account's same-day fee/expense/income order
        # while putting the newest transactions first across all accounts.
        matched_rows.sort(key=lambda row: row["account_label"].casefold())
        matched_rows.sort(key=lambda row: row["entry_date"], reverse=True)
        total = len(matched_rows)
        page_rows = matched_rows[(page - 1) * page_size:page * page_size]
        for row in page_rows:
            row.pop("_sort", None)
            row.pop("_category_code", None)
        return {
            "items": page_rows, "total": total, "page": page, "page_size": page_size,
            "summary": {
                "matching_count": total,
                "income_amount": self._amount_value(matched_income),
                "expense_amount": self._amount_value(matched_expense),
                "account_count": len(matched_accounts),
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
        category_record = None
        if values.get("direction") == "expense":
            category_record = await FinanceCategoryService(self.db).get_or_create(values.get("category"))
            values["category"] = category_record.name if category_record else None
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
            category_id=category_record.id if category_record else None,
            category_record=category_record,
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
        category_record = None
        if values.get("direction") == "expense":
            category_record = await FinanceCategoryService(self.db).get_or_create(values.get("category"))
            values["category"] = category_record.name if category_record else None

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
        entry.category_id = category_record.id if category_record else None
        entry.category_record = category_record
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
        return {
            "bank": "转账支付",
            "wechat": "微信支付",
            "alipay": "支付宝转账",
            "cash": "现金支付",
            "other": "其它支付",
        }[account.account_type]

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
