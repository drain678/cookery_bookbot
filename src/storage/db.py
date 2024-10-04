from collections.abc import AsyncGenerator

from asyncpg import Connection
from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession

from config.settings import settings

from src.model.model import Base

import asyncio

def create_engine() -> AsyncEngine:
    return create_async_engine(settings.db_url, poolclass = AsyncAdaptedQueuePool, connect_args={'connection_class': Connection,})



def create_session(_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


engine = create_engine()
async_session = create_session(engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as db:
        yield db

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_models())
