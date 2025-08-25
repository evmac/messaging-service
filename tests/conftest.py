import asyncio
import os
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base
from app.main import app

load_dotenv()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine for integration tests."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is required for integration tests. "
            "Set it to your test database URL."
        )

    engine = create_async_engine(
        database_url,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session for integration tests."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # Use nested transaction for test isolation
        async with session.begin_nested():
            yield session
            # Transaction will automatically rollback when exiting the context


@pytest.fixture(scope="function")
async def mock_db() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock database session for unit tests."""
    # Use mock to avoid database connection issues in unit tests
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()  # add is sync, not async

    yield mock_session


@pytest.fixture
def client() -> Generator[TestClient, Any, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client
