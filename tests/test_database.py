import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine


@pytest.mark.asyncio
async def test_database_connection() -> None:
    """Test that we can connect to the database."""
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_database_tables_exist() -> None:
    """Test that required tables exist."""
    try:
        async with AsyncSession(engine) as session:
            # Check if conversations table exists
            result = await session.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'conversations'
                )
            """
                )
            )
            assert result.scalar() is True

            # Check if messages table exists
            result = await session.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'messages'
                )
            """
                )
            )
            assert result.scalar() is True

            # Check if participants table exists
            result = await session.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'participants'
                )
            """
                )
            )
            assert result.scalar() is True
    finally:
        await engine.dispose()
