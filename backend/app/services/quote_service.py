from datetime import date
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.quote_repo import QuoteRepository
from app.services.number_generator import generate_quote_no, generate_order_no


class QuoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuoteRepository(db)

    async def list_quotes(self, page: int, page_size: int, status: str | None = None, customer_id: UUID | None = None,
                          keyword: str | None = None, date_from: date | None = None, date_to: date | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        quotes, total = await self.repo.list_quotes(skip=skip, limit=page_size, status=status, customer_id=customer_id,
                                                     keyword=keyword, date_from=date_from, date_to=date_to)
        return [self._quote_to_summary(q) for q in quotes], total

    async def get_quote(self, quote_id: UUID) -> dict | None:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            return None
        return self._quote_to_detail(quote)

    async def create_quote(self, data: dict) -> dict:
        data["quote_no"] = await generate_quote_no(self.db)
        data["subtotal_amount"] = Decimal("0")
        data["discount_amount"] = Decimal(str(data.pop("discount_amount", "0")))
        data["tax_rate"] = Decimal(str(data.pop("tax_rate", "0")))
        data["tax_amount"] = Decimal("0")
        data["total_amount"] = Decimal("0")
        data["status"] = "draft"

        # Convert customer_id from string to UUID if provided
        if data.get("customer_id"):
            data["customer_id"] = UUID(data["customer_id"])
        else:
            data.pop("customer_id", None)  # Remove None so model default (None) is used

        # Pass items through data so the repo can handle them
        items_data = data.get("items", [])
        for item in items_data:
            for fee_key in ("unit_price", "process_fee", "installation_fee", "design_fee", "transport_fee", "other_fee"):
                item[fee_key] = Decimal(str(item.get(fee_key, "0")))

        quote = await self.repo.create(data)

        if items_data:
            await self.calculate_quote(quote.id)

        return self._quote_to_detail(quote)

    async def update_quote(self, quote_id: UUID, data: dict) -> dict:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            raise ValueError("报价单不存在")
        if "discount_amount" in data and data["discount_amount"] is not None:
            data["discount_amount"] = Decimal(str(data["discount_amount"]))
        if "tax_rate" in data and data["tax_rate"] is not None:
            data["tax_rate"] = Decimal(str(data["tax_rate"]))
        quote = await self.repo.update(quote, data)
        return self._quote_to_detail(quote)

    async def delete_quote(self, quote_id: UUID) -> bool:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            return False
        await self.repo.soft_delete(quote)
        return True

    async def calculate_quote(self, quote_id: UUID) -> dict:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            raise ValueError("报价单不存在")

        items = await self.repo.get_items(quote_id)
        subtotal = Decimal("0")
        for item in items:
            length = Decimal(str(item.length or 0))
            width = Decimal(str(item.width or 0))
            quantity = Decimal(str(item.quantity))
            unit_price = Decimal(str(item.unit_price))
            process_fee = Decimal(str(item.process_fee))
            installation_fee = Decimal(str(item.installation_fee))
            design_fee = Decimal(str(item.design_fee))
            transport_fee = Decimal(str(item.transport_fee))
            other_fee = Decimal(str(item.other_fee))

            area = length * width * quantity
            item.area = float(area)
            item_subtotal = area * unit_price + process_fee + installation_fee + design_fee + transport_fee + other_fee
            item.subtotal_amount = float(item_subtotal)
            subtotal += item_subtotal

        discount = Decimal(str(quote.discount_amount))
        tax_rate = Decimal(str(quote.tax_rate))
        after_discount = subtotal - discount
        tax_amount = after_discount * tax_rate
        total = after_discount + tax_amount

        quote.subtotal_amount = float(subtotal)
        quote.tax_amount = float(tax_amount)
        quote.total_amount = float(total)

        await self.db.flush()
        return self._quote_to_detail(quote)

    async def confirm_quote(self, quote_id: UUID) -> dict:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            raise ValueError("报价单不存在")
        if quote.status != "draft":
            raise ValueError("只有草稿状态的报价单可以确认")
        quote.status = "confirmed"
        await self.db.flush()
        return self._quote_to_detail(quote)

    async def revert_to_draft(self, quote_id: UUID) -> dict:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            raise ValueError("报价单不存在")
        if quote.status != "confirmed":
            raise ValueError("只有已确认的报价单可以撤回")
        quote.status = "draft"
        await self.db.flush()
        return self._quote_to_detail(quote)

    async def convert_to_order(self, quote_id: UUID, created_by: UUID) -> dict:
        quote = await self.repo.get_by_id(quote_id)
        if not quote:
            raise ValueError("报价单不存在")
        if quote.status != "confirmed":
            raise ValueError("只有已确认的报价单可以转订单")

        # Auto-create customer if quote has customer_name but no customer_id
        if not quote.customer_id and quote.customer_name:
            from app.services.customer_service import CustomerService
            customer_svc = CustomerService(self.db)
            new_customer = await customer_svc.create_customer({"name": quote.customer_name})
            quote.customer_id = UUID(new_customer["id"])

        # Save version snapshot
        version_no = await self.repo.get_next_version_no(quote_id)
        snapshot = self._quote_to_detail(quote)
        await self.repo.create_version(quote_id, version_no, snapshot, created_by)

        # Create order
        from app.models.order import Order, OrderItem, OrderStatusLog
        from datetime import datetime

        order_no = await generate_order_no(self.db)
        order = Order(
            order_no=order_no,
            quote_id=quote.id,
            customer_id=quote.customer_id,
            project_name=quote.project_name,
            sales_user_id=quote.sales_user_id,
            status="pending_confirm",
            total_amount=quote.total_amount,
        )
        self.db.add(order)

        items = await self.repo.get_items(quote_id)
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                source_quote_item_id=item.id,
                item_name=item.item_name,
                product_id=item.product_id,
                material_id=item.material_id,
                process_id=item.process_id,
                length=item.length,
                width=item.width,
                height=item.height,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                subtotal_amount=item.subtotal_amount,
                remark=item.remark,
            )
            self.db.add(order_item)

        status_log = OrderStatusLog(
            order_id=order.id,
            from_status=None,
            to_status="pending_confirm",
            reason="报价转订单",
            operated_by=created_by,
            operated_at=datetime.now(),
        )
        self.db.add(status_log)

        quote.status = "converted"
        await self.db.flush()

        return {
            "id": str(order.id),
            "order_no": order.order_no,
            "customer_id": str(order.customer_id),
            "project_name": order.project_name,
            "status": order.status,
            "total_amount": order.total_amount,
        }

    def _quote_to_summary(self, q) -> dict:
        return {
            "id": str(q.id), "quote_no": q.quote_no,
            "customer_id": str(q.customer_id) if q.customer_id else None,
            "customer_name": q.customer_name,
            "project_name": q.project_name,
            "status": q.status, "total_amount": float(q.total_amount),
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }

    def _quote_to_detail(self, q) -> dict:
        return {
            "id": str(q.id), "quote_no": q.quote_no,
            "customer_id": str(q.customer_id) if q.customer_id else None,
            "customer_name": q.customer_name,
            "project_name": q.project_name,
            "sales_user_id": str(q.sales_user_id) if q.sales_user_id else None,
            "status": q.status,
            "subtotal_amount": float(q.subtotal_amount),
            "discount_amount": float(q.discount_amount),
            "tax_rate": float(q.tax_rate),
            "tax_amount": float(q.tax_amount),
            "total_amount": float(q.total_amount),
            "valid_until": q.valid_until.isoformat() if q.valid_until else None,
            "remark": q.remark,
            "created_at": q.created_at.isoformat() if q.created_at else None,
            "items": [
                {
                    "id": str(item.id), "quote_id": str(item.quote_id),
                    "product_id": str(item.product_id) if item.product_id else None,
                    "material_id": str(item.material_id) if item.material_id else None,
                    "process_id": str(item.process_id) if item.process_id else None,
                    "item_name": item.item_name,
                    "length": float(item.length) if item.length else None,
                    "width": float(item.width) if item.width else None,
                    "height": float(item.height) if item.height else None,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "area": float(item.area) if item.area else None,
                    "unit_price": float(item.unit_price),
                    "process_fee": float(item.process_fee),
                    "installation_fee": float(item.installation_fee),
                    "design_fee": float(item.design_fee),
                    "transport_fee": float(item.transport_fee),
                    "other_fee": float(item.other_fee),
                    "subtotal_amount": float(item.subtotal_amount),
                    "remark": item.remark,
                    "sort_order": item.sort_order,
                }
                for item in (q.items or [])
            ],
        }
