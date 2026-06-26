from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from realestate.config import settings

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
