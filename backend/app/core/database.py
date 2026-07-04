from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,          # 每次使用前检测连接是否有效
    pool_recycle=3600,           # 每小时回收连接，防止 PostgreSQL 断开
    pool_reset_on_return='rollback',  # 归还连接时回滚未完成的事务
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# For use outside request context (e.g., WebSocket)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
