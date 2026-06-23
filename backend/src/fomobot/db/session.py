from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fomobot.config import settings

# Async engine (FastAPI 라우터용)
async_engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    echo=settings.app_env == "development",
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine (Alembic 마이그레이션·배치용)
sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SyncSessionLocal = sessionmaker(sync_engine, autocommit=False, autoflush=False)


async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
