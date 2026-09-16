from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.job import AsyncJob

router = APIRouter()

class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress: int
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(AsyncJob).where(AsyncJob.id == job_id, AsyncJob.user_id == current_user.id))
    job = res.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    return job

@router.get("", response_model=List[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(AsyncJob)
        .where(AsyncJob.user_id == current_user.id)
        .order_by(AsyncJob.created_at.desc())
    )
    return res.scalars().all()
