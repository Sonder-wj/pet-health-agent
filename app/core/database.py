import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def init_db():
    import app.models  # noqa: F401  ensure all models are registered
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # 确保默认匿名用户存在
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            from app.core.auth import hash_password
            from app.models.user import User
            r = await session.execute(select(User).where(User.id == 1))
            if not r.scalar_one_or_none():
                session.add(User(
                    id=1, username="anonymous", email="anonymous@local",
                    password_hash=hash_password("anonymous"),
                    is_active=True,
                ))
                await session.commit()
    except Exception as e:
        if "Can't connect" in str(e) or "Connection refused" in str(e):
            pass  # MySQL unavailable, skip persistence
        else:
            raise


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
