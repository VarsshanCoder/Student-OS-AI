import asyncio
import logging
import traceback
from typing import Callable, Coroutine, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job import AsyncJob
from app.core.database import async_sessionmaker

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self._registry: Dict[str, Callable[[str, AsyncSession, Dict[str, Any]], Coroutine[Any, Any, None]]] = {}

    def register_handler(self, job_type: str, handler: Callable[[str, AsyncSession, Dict[str, Any]], Coroutine[Any, Any, None]]):
        """Registers an async handler function for a specific job type."""
        self._registry[job_type] = handler

    async def create_job(
        self,
        db: AsyncSession,
        user_id: str,
        job_type: str,
        parameters: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> AsyncJob:
        """Creates a job, or returns an existing one if idempotency_key matches and it hasn't failed."""
        if idempotency_key:
            existing = await db.execute(
                select(AsyncJob).where(AsyncJob.idempotency_key == idempotency_key)
            )
            job = existing.scalar_one_or_none()
            if job and job.status not in ("failed",):
                return job

        job = AsyncJob(
            user_id=user_id,
            job_type=job_type,
            status="queued",
            parameters=parameters,
            idempotency_key=idempotency_key
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        # Fire off the worker loop in the background for this job
        asyncio.create_task(self._process_job_safe(job.id))
        return job

    async def update_job(
        self,
        db: AsyncSession,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> AsyncJob:
        res = await db.execute(select(AsyncJob).where(AsyncJob.id == job_id))
        job = res.scalar_one_or_none()
        if not job:
            return None
            
        if status: job.status = status
        if progress is not None: job.progress = progress
        if message: job.message = message
        if result: job.result = result
        if error: job.error = error
        
        await db.commit()
        await db.refresh(job)
        return job

    async def _process_job_safe(self, job_id: str):
        """Wrapper to provide a fresh DB session and catch all exceptions."""
        from app.core.database import engine
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        
        SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
        async with SessionLocal() as db:
            # Mark as processing immediately
            job = await self.update_job(db, job_id, status="processing", progress=0)
            if not job: return
            
            handler = self._registry.get(job.job_type)
            if not handler:
                await self.update_job(db, job_id, status="failed", error=f"No handler registered for {job.job_type}")
                return
                
            try:
                # The handler must update the job's progress itself.
                await handler(job_id, db, job.parameters or {})
                # If the handler succeeds without updating status to completed, we do it.
                # However, usually handlers update their own final status + result.
                final_check = await db.execute(select(AsyncJob).where(AsyncJob.id == job_id))
                final_job = final_check.scalar_one_or_none()
                if final_job and final_job.status not in ("completed", "failed"):
                    await self.update_job(db, job_id, status="completed", progress=100)
            except asyncio.CancelledError:
                await self.update_job(db, job_id, status="failed", error="Job was cancelled or worker restarted")
                raise
            except Exception as e:
                err_str = f"{str(e)}\n{traceback.format_exc()}"
                logger.error(f"Job {job_id} failed: {err_str}")
                await self.update_job(db, job_id, status="failed", error=err_str)

    async def recover_jobs(self):
        """Called on app startup to recover queued/processing jobs that were interrupted."""
        from app.core.database import engine
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(AsyncJob).where(AsyncJob.status.in_(["queued", "processing", "extracting", "chunking", "embedding", "indexing", "generating", "validating"]))
            )
            jobs = result.scalars().all()
            for job in jobs:
                logger.info(f"Recovering interrupted job {job.id} ({job.job_type})")
                asyncio.create_task(self._process_job_safe(job.id))

job_manager = JobManager()
