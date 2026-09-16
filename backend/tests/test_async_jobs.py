import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.job import AsyncJob
from app.worker.manager import JobManager
from app.core.database import Base

from sqlalchemy.pool import StaticPool

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=StaticPool)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# Need to monkeypatch the job_manager's SessionLocal temporarily for testing
import app.worker.manager
app.worker.manager.engine = test_engine

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_job_idempotency_and_execution():
    async with TestingSessionLocal() as db:
        user = User(email="job@test.com", password_hash="hash", full_name="Job User")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        manager = JobManager()
        
        # Define mock handler
        async def mock_handler(job_id, session, params):
            await manager.update_job(session, job_id, status="extracting", progress=50)
            await asyncio.sleep(0.1)
            await manager.update_job(session, job_id, status="completed", progress=100, result={"done": True})

        manager.register_handler("test_job", mock_handler)
        
        # Monkey patch internal session generation for SQLite testing
        async def _mock_process_job_safe(job_id):
            print("MOCK PROCESS TRIGGERED")
            async with TestingSessionLocal() as session:
                job = await manager.update_job(session, job_id, status="processing", progress=0)
                try:
                    await mock_handler(job_id, session, job.parameters)
                except Exception as e:
                    print("MOCK FAILED", e)
                    await manager.update_job(session, job_id, status="failed", error=str(e))
                    
        manager._process_job_safe = _mock_process_job_safe

        # Create first job
        job1 = await manager.create_job(
            db, user_id=user.id, job_type="test_job", parameters={"x": 1}, idempotency_key="key1"
        )
        assert job1.status == "queued"
        
        # Idempotency check: should return same job
        job2 = await manager.create_job(
            db, user_id=user.id, job_type="test_job", parameters={"x": 1}, idempotency_key="key1"
        )
        assert job1.id == job2.id
        
        # Wait for execution
        await asyncio.sleep(0.3)
        
        job_id = job1.id
        db.expire_all()
        res = await db.execute(select(AsyncJob).where(AsyncJob.id == job_id))
        final_job = res.scalar_one()
        assert final_job.status == "completed"
        assert final_job.progress == 100
        assert final_job.result == {"done": True}
