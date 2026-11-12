"""Resolve and rename canonical finance categories without altering amounts."""
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.models.bank_ledger import BankLedgerEntry
from app.models.finance_category import FinanceCategory, FinanceCategoryAlias
from app.models.project_cost import ProjectCost


class FinanceCategoryService:
    def __init__(self, db):
        self.db = db

    async def list_categories(self) -> list[FinanceCategory]:
        result = await self.db.execute(
            select(FinanceCategory).order_by(FinanceCategory.sort_order, FinanceCategory.name)
        )
        return list(result.scalars().all())

    async def get_or_create(self, raw_name: str | None) -> FinanceCategory | None:
        name = (raw_name or "").strip()
        if not name:
            return None

        category = await self.db.scalar(select(FinanceCategory).where(FinanceCategory.name == name))
        if category is not None:
            return category

        alias = await self.db.scalar(
            select(FinanceCategoryAlias).where(FinanceCategoryAlias.alias == name)
        )
        if alias is not None:
            category = await self.db.get(FinanceCategory, alias.category_id)
            if category is not None:
                return category

        last_sort_order = await self.db.scalar(select(func.max(FinanceCategory.sort_order)))
        await self.db.execute(
            insert(FinanceCategory)
            .values(
                id=uuid4(),
                name=name,
                code=f"custom_{uuid4().hex}",
                sort_order=(last_sort_order or 0) + 1,
            )
            .on_conflict_do_nothing(index_elements=[FinanceCategory.name])
        )
        category = await self.db.scalar(select(FinanceCategory).where(FinanceCategory.name == name))
        if category is not None:
            return category

        # A concurrent rename may have made the submitted legacy label an alias.
        alias = await self.db.scalar(
            select(FinanceCategoryAlias).where(FinanceCategoryAlias.alias == name)
        )
        if alias is not None:
            return await self.db.get(FinanceCategory, alias.category_id)
        raise ValueError("分类保存失败，请重试")

    async def rename(self, category_id: UUID, raw_name: str) -> dict:
        name = raw_name.strip()
        category = await self.db.scalar(
            select(FinanceCategory)
            .where(FinanceCategory.id == category_id)
            .with_for_update()
        )
        if category is None:
            raise ValueError("财务分类不存在")

        old_name = category.name
        if name == old_name:
            return {
                "id": str(category.id),
                "name": name,
                "previous_name": old_name,
                "updated_bank_ledger_entries": 0,
                "updated_project_costs": 0,
            }

        existing = await self.db.scalar(
            select(FinanceCategory.id).where(FinanceCategory.name == name)
        )
        if existing is not None and existing != category.id:
            raise ValueError("同名分类已存在，不能直接改名合并")

        alias_conflict = await self.db.scalar(
            select(FinanceCategoryAlias).where(FinanceCategoryAlias.alias == name)
        )
        if alias_conflict is not None and alias_conflict.category_id != category.id:
            raise ValueError("该名称已映射到其他分类，不能直接改名合并")
        old_alias = await self.db.scalar(
            select(FinanceCategoryAlias).where(FinanceCategoryAlias.alias == old_name)
        )
        if old_alias is not None and old_alias.category_id != category.id:
            raise ValueError("原分类名称已映射到其他分类，无法安全改名")

        if alias_conflict is not None:
            await self.db.delete(alias_conflict)
        if old_alias is None:
            self.db.add(FinanceCategoryAlias(alias=old_name, category_id=category.id))

        category.name = name
        await self.db.flush()
        ledger_result = await self.db.execute(
            update(BankLedgerEntry)
            .where(BankLedgerEntry.category_id == category.id)
            .values(category=name)
        )
        cost_result = await self.db.execute(
            update(ProjectCost)
            .where(ProjectCost.category_id == category.id)
            .values(category=name)
        )
        await self.db.flush()
        return {
            "id": str(category.id),
            "name": category.name,
            "previous_name": old_name,
            "updated_bank_ledger_entries": max(ledger_result.rowcount or 0, 0),
            "updated_project_costs": max(cost_result.rowcount or 0, 0),
        }
