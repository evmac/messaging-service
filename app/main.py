import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import close_db, get_db, init_db
from app.routers.conversations import router as conversations_router
from app.routers.messages import router as messages_router
from app.routers.webhooks import router as webhooks_router

# Load environment variables
load_dotenv()

# Environment variable parsing
ENV = os.getenv("ENV")
ENV_IS_PROD = ENV == "prod"
COMMIT_HASH = os.getenv("COMMIT_HASH")
if not COMMIT_HASH and ENV_IS_PROD:
    raise ValueError("COMMIT_HASH is required for production environments")

APP_ADDR = os.getenv("HOST", "0.0.0.0")
APP_PORT = int(os.getenv("PORT", "8000"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Messaging Service",
    description="Unified messaging API for SMS/MMS and Email",
    version=COMMIT_HASH,
    lifespan=lifespan,
)

# Include routers
app.include_router(
    conversations_router, prefix="/api/conversations", tags=["conversations"]
)
app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Health check endpoint with database connectivity."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        db_status = "connected" if result.scalar() == 1 else "error"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "environment": ENV,
        "version": COMMIT_HASH,
    }


# If run directly, start the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_ADDR, port=APP_PORT)
