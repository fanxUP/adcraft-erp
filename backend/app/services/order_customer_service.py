"""报价转订单时的客户主数据补齐。"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_document_customer(
    db: AsyncSession,
    document,
    created_by: UUID,
) -> None:
    """自由输入客户的报价转订单时，建立正式客户及主联系人。"""
    if document.customer_id:
        return
    customer_name = (document.customer_name or "").strip()
    if not customer_name:
        raise ValueError("报价缺少客户，无法转为订单")

    from app.models.customer import Customer, CustomerContact
    from app.services.number_generator import generate_customer_no

    customer = Customer(
        customer_no=await generate_customer_no(db),
        name=customer_name,
        phone=document.contact_phone,
        created_by=created_by,
        remark=f"由报价 {document.doc_no} 转订单时自动建立",
    )
    db.add(customer)
    await db.flush()
    if document.contact_person:
        db.add(
            CustomerContact(
                customer_id=customer.id,
                name=document.contact_person,
                phone=document.contact_phone,
                is_primary=True,
            )
        )
    document.customer_id = customer.id
    await db.flush()
