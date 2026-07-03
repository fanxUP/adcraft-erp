from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def _generate_no(db: AsyncSession, prefix: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    pattern = f"{prefix}{today}-%"

    if prefix == "Q":
        from app.models.quote import Quote
        result = await db.execute(
            select(Quote.quote_no).where(Quote.quote_no.like(pattern)).order_by(Quote.quote_no.desc()).limit(1)
        )
    elif prefix == "O":
        from app.models.order import Order
        result = await db.execute(
            select(Order.order_no).where(Order.order_no.like(pattern)).order_by(Order.order_no.desc()).limit(1)
        )
    elif prefix == "C":
        from app.models.customer import Customer
        result = await db.execute(
            select(Customer.customer_no).where(Customer.customer_no.like(pattern)).order_by(Customer.customer_no.desc()).limit(1)
        )
    elif prefix == "D":
        from app.models.task import DesignTask
        result = await db.execute(
            select(DesignTask.design_no).where(DesignTask.design_no.like(pattern)).order_by(DesignTask.design_no.desc()).limit(1)
        )
    elif prefix == "P":
        from app.models.task import ProductionTask
        result = await db.execute(
            select(ProductionTask.production_no).where(ProductionTask.production_no.like(pattern)).order_by(ProductionTask.production_no.desc()).limit(1)
        )
    elif prefix == "I":
        from app.models.task import InstallationTask
        result = await db.execute(
            select(InstallationTask.installation_no).where(InstallationTask.installation_no.like(pattern)).order_by(InstallationTask.installation_no.desc()).limit(1)
        )
    elif prefix == "PAY":
        from app.models.payment import Payment
        result = await db.execute(
            select(Payment.payment_no).where(Payment.payment_no.like(pattern)).order_by(Payment.payment_no.desc()).limit(1)
        )
    elif prefix == "STMT":
        from app.models.payment import CustomerStatement
        result = await db.execute(
            select(CustomerStatement.statement_no).where(CustomerStatement.statement_no.like(pattern)).order_by(CustomerStatement.statement_no.desc()).limit(1)
        )
    elif prefix == "EXP":
        from app.models.payment import Expense
        result = await db.execute(
            select(Expense.expense_no).where(Expense.expense_no.like(pattern)).order_by(Expense.expense_no.desc()).limit(1)
        )
    elif prefix == "V":
        from app.models.outsource import OutsourceVendor
        result = await db.execute(
            select(OutsourceVendor.vendor_no).where(OutsourceVendor.vendor_no.like(pattern)).order_by(OutsourceVendor.vendor_no.desc()).limit(1)
        )
    elif prefix == "OT":
        from app.models.outsource import OutsourceTask
        result = await db.execute(
            select(OutsourceTask.task_no).where(OutsourceTask.task_no.like(pattern)).order_by(OutsourceTask.task_no.desc()).limit(1)
        )
    elif prefix == "OP":
        from app.models.outsource import OutsourcePayment
        result = await db.execute(
            select(OutsourcePayment.payment_no).where(OutsourcePayment.payment_no.like(pattern)).order_by(OutsourcePayment.payment_no.desc()).limit(1)
        )
    elif prefix == "COST":
        from app.models.project_cost import ProjectCost
        result = await db.execute(
            select(ProjectCost.cost_no).where(ProjectCost.cost_no.like(pattern)).order_by(ProjectCost.cost_no.desc()).limit(1)
        )
    elif prefix == "A":
        from app.models.acceptance import AcceptanceForm
        result = await db.execute(
            select(AcceptanceForm.acceptance_no).where(AcceptanceForm.acceptance_no.like(pattern)).order_by(AcceptanceForm.acceptance_no.desc()).limit(1)
        )
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
