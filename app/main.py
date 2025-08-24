import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import close_db, get_db, init_db

# Load environment variables
load_dotenv()

# Environment variable parsing
COMMIT_HASH = os.getenv("COMMIT_HASH", "unknown")
APP_ADDR = os.getenv("HOST", "127.0.0.1")  # Default to localhost for security
APP_PORT = int(os.getenv("PORT", "8080"))


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
        "version": COMMIT_HASH,
    }


# If run directly, start the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_ADDR, port=APP_PORT)
