from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Numeric, cast, func, select, text


EMPLOYEE_NUMBER_LOCK_ID = 9_240_321_991


async def _generate_no(db: AsyncSession, prefix: str) -> str:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    if prefix != "EMP":
        lock_id = int.from_bytes(hashlib.sha256(f"adcraft-number:{prefix}:{today}".encode()).digest()[:8], "big", signed=True)
        await db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
    pattern = f"{prefix}{today}-%"

    if prefix in ("O", "S"):
        from app.models.business_document import BusinessDocument
        result = await db.execute(
            select(BusinessDocument.doc_no).where(
                BusinessDocument.doc_no.like(pattern)
            ).where(BusinessDocument.doc_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(BusinessDocument.doc_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "C":
        from app.models.customer import Customer
        result = await db.execute(
            select(Customer.customer_no).where(Customer.customer_no.like(pattern)).where(Customer.customer_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(Customer.customer_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "D":
        from app.models.task import DesignTask
        result = await db.execute(
            select(DesignTask.design_no).where(DesignTask.design_no.like(pattern)).where(DesignTask.design_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(DesignTask.design_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "P":
        from app.models.task import ProductionTask
        result = await db.execute(
            select(ProductionTask.production_no).where(ProductionTask.production_no.like(pattern)).where(ProductionTask.production_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(ProductionTask.production_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "I":
        from app.models.task import InstallationTask
        result = await db.execute(
            select(InstallationTask.installation_no).where(InstallationTask.installation_no.like(pattern)).where(InstallationTask.installation_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(InstallationTask.installation_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "PAY":
        from app.models.payment import Payment
        result = await db.execute(
            select(Payment.payment_no).where(Payment.payment_no.like(pattern)).where(Payment.payment_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(Payment.payment_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "STMT":
        from app.models.payment import CustomerStatement
        result = await db.execute(
            select(CustomerStatement.statement_no).where(CustomerStatement.statement_no.like(pattern)).where(CustomerStatement.statement_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(CustomerStatement.statement_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "EXP":
        from app.models.payment import Expense
        result = await db.execute(
            select(Expense.expense_no).where(Expense.expense_no.like(pattern)).where(Expense.expense_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(Expense.expense_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "APP":
        from app.models.payable import PayablePayment
        result = await db.execute(
            select(PayablePayment.payment_no).where(
                PayablePayment.payment_no.like(pattern)
            ).where(PayablePayment.payment_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(PayablePayment.payment_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "Q":
        from app.models.business_document import BusinessDocument
        result = await db.execute(
            select(BusinessDocument.doc_no).where(
                BusinessDocument.doc_type == "quote",
                BusinessDocument.doc_no.like(pattern),
            ).where(BusinessDocument.doc_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(BusinessDocument.doc_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "SO":
        # 兼容旧销售单编号格式
        from app.models.business_document import BusinessDocument
        result = await db.execute(
            select(BusinessDocument.doc_no).where(
                BusinessDocument.doc_no.like(pattern)
            ).where(BusinessDocument.doc_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(BusinessDocument.doc_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "V":
        from app.models.outsource import OutsourceVendor
        result = await db.execute(
            select(OutsourceVendor.vendor_no).where(OutsourceVendor.vendor_no.like(pattern)).where(OutsourceVendor.vendor_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(OutsourceVendor.vendor_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "OT":
        from app.models.outsource import OutsourceTask
        result = await db.execute(
            select(OutsourceTask.task_no).where(OutsourceTask.task_no.like(pattern)).where(OutsourceTask.task_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(OutsourceTask.task_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "OP":
        from app.models.outsource import OutsourcePayment
        result = await db.execute(
            select(OutsourcePayment.payment_no).where(OutsourcePayment.payment_no.like(pattern)).where(OutsourcePayment.payment_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(OutsourcePayment.payment_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "COST":
        from app.models.project_cost import ProjectCost
        today_short = today[2:]
        pattern = f"{today_short}-%"
        result = await db.execute(
            select(ProjectCost.cost_no).where(ProjectCost.cost_no.like(pattern)).where(ProjectCost.cost_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(ProjectCost.cost_no, "-", 2), Numeric).desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        if last:
            seq = int(last.split("-")[1]) + 1
        else:
            seq = 1
        return f"{today_short}-{seq:03d}"
    elif prefix == "A":
        from app.models.acceptance import AcceptanceForm
        result = await db.execute(
            select(AcceptanceForm.acceptance_no).where(AcceptanceForm.acceptance_no.like(pattern)).where(AcceptanceForm.acceptance_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(AcceptanceForm.acceptance_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "CT":
        from app.models.contract import Contract
        result = await db.execute(
            select(Contract.contract_no).where(Contract.contract_no.like(pattern)).where(Contract.contract_no.op("~")(r"^[A-Za-z]*[0-9]+-[0-9]+$")).order_by(cast(func.split_part(Contract.contract_no, "-", 2), Numeric).desc()).limit(1)
        )
    elif prefix == "EMP":
        # 员工工号：纯数字序列（现有格式 001/002/...），取最大值 +1
        from app.models.employee import Employee
        # The max-plus-one query is serialized inside the transaction.  The
        # unique constraint remains the final guard, while this prevents two
        # concurrent employee creates from normally selecting the same number.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": EMPLOYEE_NUMBER_LOCK_ID},
        )
        result = await db.execute(
            select(Employee.employee_no).where(Employee.employee_no.op("~")(r"^[0-9]+$")).order_by(cast(Employee.employee_no, Numeric).desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        if last:
            try:
                seq = int(last) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"{seq:03d}"
    else:
        raise ValueError(f"Unknown prefix: {prefix}")

    last = result.scalar_one_or_none()
    if last:
        seq = int(last.split("-")[1]) + 1
    else:
        seq = 1

    return f"{prefix}{today}-{seq:04d}"


async def generate_quote_no(db: AsyncSession) -> str:
    return await _generate_no(db, "Q")


async def generate_order_no(db: AsyncSession) -> str:
    return await _generate_no(db, "O")


async def generate_customer_no(db: AsyncSession) -> str:
    return await _generate_no(db, "C")


async def generate_design_no(db: AsyncSession) -> str:
    return await _generate_no(db, "D")


async def generate_production_no(db: AsyncSession) -> str:
    return await _generate_no(db, "P")


async def generate_installation_no(db: AsyncSession) -> str:
    return await _generate_no(db, "I")


async def generate_payment_no(db: AsyncSession) -> str:
    return await _generate_no(db, "PAY")


async def generate_statement_no(db: AsyncSession) -> str:
    return await _generate_no(db, "STMT")


async def generate_expense_no(db: AsyncSession) -> str:
    return await _generate_no(db, "EXP")


async def generate_payable_payment_no(db: AsyncSession) -> str:
    return await _generate_no(db, "APP")


async def generate_vendor_no(db: AsyncSession) -> str:
    return await _generate_no(db, "V")


async def generate_outsource_task_no(db: AsyncSession) -> str:
    return await _generate_no(db, "OT")


async def generate_outsource_payment_no(db: AsyncSession) -> str:
    return await _generate_no(db, "OP")


async def generate_project_cost_no(db: AsyncSession) -> str:
    return await _generate_no(db, "COST")


async def generate_acceptance_no(db: AsyncSession) -> str:
    return await _generate_no(db, "A")


async def generate_contract_no(db: AsyncSession) -> str:
    return await _generate_no(db, "CT")


async def generate_employee_no(db):
    return await _generate_no(db, "EMP")
