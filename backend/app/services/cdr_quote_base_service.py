from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cdr_quote_repo import CdrQuoteRepository
from app.services.price_engine import PriceEngine


class CdrQuoteServiceBase:
    """CDR 报价子领域共享依赖。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CdrQuoteRepository(db)
        self.engine = PriceEngine()
