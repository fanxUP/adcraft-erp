from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repo import ProductRepository


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProductRepository(db)

    # Categories
    async def list_categories(self) -> list[dict]:
        cats = await self.repo.list_categories()
        return [{"id": str(c.id), "name": c.name, "parent_id": str(c.parent_id) if c.parent_id else None, "sort_order": c.sort_order} for c in cats]

    async def create_category(self, data: dict) -> dict:
        cat = await self.repo.create_category(data)
        return {"id": str(cat.id), "name": cat.name, "parent_id": str(cat.parent_id) if cat.parent_id else None, "sort_order": cat.sort_order}

    async def delete_category(self, cat_id: UUID) -> bool:
        return await self.repo.delete_category(cat_id)

    # Products
    async def list_products(self, page: int, page_size: int, keyword: str | None = None, category_id: UUID | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        products, total = await self.repo.list_products(skip=skip, limit=page_size, keyword=keyword, category_id=category_id)
        return [self._product_to_dict(p) for p in products], total

    async def get_product(self, product_id: UUID) -> dict | None:
        p = await self.repo.get_product_by_id(product_id)
        return self._product_to_dict(p) if p else None

    async def create_product(self, data: dict) -> dict:
        p = await self.repo.create_product(data)
        return self._product_to_dict(p)

    async def update_product(self, product_id: UUID, data: dict) -> dict:
        p = await self.repo.get_product_by_id(product_id)
        if not p:
            raise ValueError("产品不存在")
        p = await self.repo.update_product(p, data)
        return self._product_to_dict(p)

    async def delete_product(self, product_id: UUID) -> bool:
        p = await self.repo.get_product_by_id(product_id)
        if not p:
            return False
        p.is_active = False
        await self.db.flush()
        return True

    def _product_to_dict(self, p) -> dict:
        return {
            "id": str(p.id), "category_id": str(p.category_id) if p.category_id else None,
            "name": p.name, "unit": p.unit, "pricing_method": p.pricing_method,
            "default_price": float(p.default_price), "min_charge": float(p.min_charge),
            "remark": p.remark, "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    # Materials
    async def list_materials(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        materials, total = await self.repo.list_materials(skip=skip, limit=page_size, keyword=keyword)
        return [self._material_to_dict(m) for m in materials], total

    async def get_material(self, material_id: UUID) -> dict | None:
        m = await self.repo.get_material_by_id(material_id)
        return self._material_to_dict(m) if m else None

    async def create_material(self, data: dict) -> dict:
        m = await self.repo.create_material(data)
        return self._material_to_dict(m)

    async def update_material(self, material_id: UUID, data: dict) -> dict:
        m = await self.repo.get_material_by_id(material_id)
        if not m:
            raise ValueError("材质不存在")
        m = await self.repo.update_material(m, data)
        return self._material_to_dict(m)

    async def delete_material(self, material_id: UUID) -> bool:
        m = await self.repo.get_material_by_id(material_id)
        if not m:
            return False
        m.is_active = False
        await self.db.flush()
        return True

    def _material_to_dict(self, m) -> dict:
        return {
            "id": str(m.id), "name": m.name, "spec": m.spec, "unit": m.unit,
            "purchase_price": float(m.purchase_price), "sale_price": float(m.sale_price),
            "loss_rate": float(m.loss_rate), "safe_stock": float(m.safe_stock),
            "remark": m.remark, "is_active": m.is_active,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    # Processes
    async def list_processes(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        processes, total = await self.repo.list_processes(skip=skip, limit=page_size, keyword=keyword)
        return [self._process_to_dict(pr) for pr in processes], total

    async def get_process(self, process_id: UUID) -> dict | None:
        pr = await self.repo.get_process_by_id(process_id)
        return self._process_to_dict(pr) if pr else None

    async def create_process(self, data: dict) -> dict:
        pr = await self.repo.create_process(data)
        return self._process_to_dict(pr)

    async def update_process(self, process_id: UUID, data: dict) -> dict:
        pr = await self.repo.get_process_by_id(process_id)
        if not pr:
            raise ValueError("工艺不存在")
        pr = await self.repo.update_process(pr, data)
        return self._process_to_dict(pr)

    async def delete_process(self, process_id: UUID) -> bool:
        pr = await self.repo.get_process_by_id(process_id)
        if not pr:
            return False
        pr.is_active = False
        await self.db.flush()
        return True

    def _process_to_dict(self, pr) -> dict:
        return {
            "id": str(pr.id), "name": pr.name, "charge_method": pr.charge_method,
            "default_price": float(pr.default_price), "remark": pr.remark, "is_active": pr.is_active,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
        }

    # Suppliers
    async def list_suppliers(self, page: int, page_size: int, keyword: str | None = None) -> tuple[list, int]:
        skip = (page - 1) * page_size
        suppliers, total = await self.repo.list_suppliers(skip=skip, limit=page_size, keyword=keyword)
        return [self._supplier_to_dict(s) for s in suppliers], total

    async def get_supplier(self, supplier_id: UUID) -> dict | None:
        s = await self.repo.get_supplier_by_id(supplier_id)
        return self._supplier_to_dict(s) if s else None

    async def create_supplier(self, data: dict) -> dict:
        s = await self.repo.create_supplier(data)
        return self._supplier_to_dict(s)

    async def update_supplier(self, supplier_id: UUID, data: dict) -> dict:
        s = await self.repo.get_supplier_by_id(supplier_id)
        if not s:
            raise ValueError("供应商不存在")
        s = await self.repo.update_supplier(s, data)
        return self._supplier_to_dict(s)

    async def delete_supplier(self, supplier_id: UUID) -> bool:
        s = await self.repo.get_supplier_by_id(supplier_id)
        if not s:
            return False
        s.is_active = False
        await self.db.flush()
        return True

    def _supplier_to_dict(self, s) -> dict:
        return {
            "id": str(s.id),
            "supplier_no": s.supplier_no,
            "name": s.name,
            "contact_person": s.contact_person,
            "phone": s.phone,
            "address": s.address,
            "supply_type": s.supply_type,
            "bank_account": s.bank_account,
            "remark": s.remark,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
