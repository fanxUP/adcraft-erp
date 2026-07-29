"""Application-start synchronization for the AI business-rule registry."""

from app.ai_assistant.business_rules.service import BusinessRuleSyncService
from app.core.database import AsyncSessionLocal


async def synchronize_business_rules_at_startup() -> dict:
    """Synchronize in one transaction before the application serves AI traffic."""
    async with AsyncSessionLocal() as db:
        try:
            result = await BusinessRuleSyncService(db).synchronize()
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise
