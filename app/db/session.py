from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


database_url = f"postgresql+asyncpg://postgres.reyyarznpztvshewnmji:{settings.DB_PASSWORD}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
engine = create_async_engine(database_url,
                             pool_size=10,
                             max_overflow=10,
                             pool_timeout=30,
                             pool_recycle=3600,
                             echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session():
    """Async generator function that provides a database session.

    Yields:
        AsyncSession: An instance of the database session.

    Ensures that the session is properly closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


