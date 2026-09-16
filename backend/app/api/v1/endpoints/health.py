from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/live", tags=["health"])
async def liveness_check():
    """
    Liveness probe: returns 200 if the application is running.
    Does not check dependencies (DB, Redis, etc).
    """
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@router.get("/ready", tags=["health"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe: returns 200 if the application is ready to accept traffic.
    Checks database connection.
    """
    db_status = "offline"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "online"
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    is_ready = db_status == "online"
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "database": db_status,
        "environment": settings.ENVIRONMENT
    }
