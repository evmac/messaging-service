import asyncio
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Currently uses PostgreSQL with transaction rollback for test isolation.
    """
    # Create a new session for each test
    session = AsyncSessionLocal()
    try:
        # Start a transaction that will be rolled back
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Rollback to clean up any changes made during the test
            await transaction.rollback()
    finally:
        await session.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
