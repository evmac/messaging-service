"""Database configuration and connection management."""

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Load environment variables from .env file
load_dotenv()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Database configuration from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create async engine
engine = create_async_engine(
    DATABASE_URL, echo=os.getenv("SQL_DEBUG", "false").lower() == "true", future=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection on startup."""
    # Could be extended to run migrations or other startup tasks
    pass


async def close_db() -> None:
    """Close database connections on shutdown."""
    await engine.dispose()
