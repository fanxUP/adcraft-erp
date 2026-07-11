"""Backfill order_items fields from their source quote_items.

Run: cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/backfill_order_items.py
"""
import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker


FIELDS_TO_COPY = [
    "length_unit", "width_unit", "height_unit",
    "use_area", "quantity_mode", "area",
    "process_fee", "installation_fee", "design_fee", "transport_fee", "other_fee",
    "sort_order", "group_name", "material_process",
]


async def main():
    async with async_session_maker() as session:
        # Find order items that have a source quote item
        result = await session.execute(text(
            "SELECT oi.id, oi.source_quote_item_id "
            "FROM order_items oi "
            "WHERE oi.source_quote_item_id IS NOT NULL"
        ))
        rows = result.fetchall()
        print(f"Found {len(rows)} order items with source quote items")

        updated = 0
        for row in rows:
            order_item_id, quote_item_id = row
            # Get the quote item data
            cols = ", ".join(FIELDS_TO_COPY)
            qi = await session.execute(
                text(f"SELECT {cols} FROM quote_items WHERE id = :qid"),
                {"qid": quote_item_id},
            )
            qi_row = qi.fetchone()
            if not qi_row:
                continue

            set_parts = []
            params = {"oid": order_item_id}
            for i, field in enumerate(FIELDS_TO_COPY):
                val = qi_row[i]
                if val is None:
                    set_parts.append(f"{field} = NULL")
                else:
                    param_name = f"val_{i}"
                    set_parts.append(f"{field} = :{param_name}")
                    params[param_name] = val

            await session.execute(
                text(f"UPDATE order_items SET {', '.join(set_parts)} WHERE id = :oid"),
                params,
            )
            updated += 1

        await session.commit()
        print(f"Updated {updated} order items")


if __name__ == "__main__":
    asyncio.run(main())
