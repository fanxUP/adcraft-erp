from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.product import ProductCategory, Product, Material, Process, Supplier


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Categories
    async def list_categories(self) -> list[ProductCategory]:
        result = await self.db.execute(select(ProductCategory).order_by(ProductCategory.sort_order))
        return list(result.scalars().all())

    async def create_category(self, data: dict) -> ProductCategory:
        cat = ProductCategory(**data)
        self.db.add(cat)
        await self.db.flush()
        return cat

    async def delete_category(self, cat_id: UUID) -> bool:
        cat = (await self.db.execute(select(ProductCategory).where(ProductCategory.id == cat_id))).scalar_one_or_none()
        if not cat:
            return False
        await self.db.delete(cat)
        await self.db.flush()
        return True

    # Products
    async def get_product_by_id(self, product_id: UUID) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def list_products(self, skip: int = 0, limit: int = 20, keyword: str | None = None, category_id: UUID | None = None) -> tuple[list[Product], int]:
        q = select(Product)
        if keyword:
            q = q.where(Product.name.ilike(f"%{keyword}%"))
        if category_id:
            q = q.where(Product.category_id == category_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Product.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_product(self, data: dict) -> Product:
        product = Product(**data)
        self.db.add(product)
        await self.db.flush()
        return product

    async def update_product(self, product: Product, data: dict) -> Product:
        for k, v in data.items():
            if v is not None:
                setattr(product, k, v)
        await self.db.flush()
        return product

    async def delete_product(self, product: Product) -> None:
        await self.db.delete(product)
        await self.db.flush()

    # Materials
    async def get_material_by_id(self, material_id: UUID) -> Material | None:
        result = await self.db.execute(select(Material).where(Material.id == material_id))
        return result.scalar_one_or_none()

    async def list_materials(self, skip: int = 0, limit: int = 20, keyword: str | None = None) -> tuple[list[Material], int]:
        q = select(Material)
        if keyword:
            q = q.where(Material.name.ilike(f"%{keyword}%"))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Material.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_material(self, data: dict) -> Material:
        material = Material(**data)
        self.db.add(material)
        await self.db.flush()
        return material

    async def update_material(self, material: Material, data: dict) -> Material:
        for k, v in data.items():
            if v is not None:
                setattr(material, k, v)
        await self.db.flush()
        return material

    async def delete_material(self, material: Material) -> None:
        await self.db.delete(material)
        await self.db.flush()

    # Processes
    async def get_process_by_id(self, process_id: UUID) -> Process | None:
        result = await self.db.execute(select(Process).where(Process.id == process_id))
        return result.scalar_one_or_none()

    async def list_processes(self, skip: int = 0, limit: int = 20, keyword: str | None = None) -> tuple[list[Process], int]:
        q = select(Process)
        if keyword:
            q = q.where(Process.name.ilike(f"%{keyword}%"))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Process.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_process(self, data: dict) -> Process:
        process = Process(**data)
        self.db.add(process)
        await self.db.flush()
        return process

    async def update_process(self, process: Process, data: dict) -> Process:
        for k, v in data.items():
            if v is not None:
                setattr(process, k, v)
        await self.db.flush()
        return process

    async def delete_process(self, process: Process) -> None:
        await self.db.delete(process)
        await self.db.flush()

    # Suppliers
    async def get_supplier_by_id(self, supplier_id: UUID) -> Supplier | None:
        result = await self.db.execute(select(Supplier).where(Supplier.id == supplier_id))
        return result.scalar_one_or_none()

    async def list_suppliers(self, skip: int = 0, limit: int = 20, keyword: str | None = None) -> tuple[list[Supplier], int]:
        q = select(Supplier)
        if keyword:
            q = q.where(Supplier.name.ilike(f"%{keyword}%"))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()
        q = q.order_by(Supplier.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def create_supplier(self, data: dict) -> Supplier:
        supplier = Supplier(**data)
        self.db.add(supplier)
        await self.db.flush()
        return supplier

    async def update_supplier(self, supplier: Supplier, data: dict) -> Supplier:
        for k, v in data.items():
            if v is not None:
                setattr(supplier, k, v)
        await self.db.flush()
        return supplier

    async def delete_supplier(self, supplier: Supplier) -> None:
        await self.db.delete(supplier)
        await self.db.flush()
