import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.models.user import User
from app.models.knowledge_book import KnowledgeBook, KnowledgeChapter
from app.models.job import AsyncJob
from app.worker.manager import JobManager
from app.core.database import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=StaticPool)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# Monkeypatch the global job manager
import app.worker.manager
app.worker.manager.engine = test_engine

from app.worker.handlers.book_handler import process_knowledge_book_job, process_chapter_retry_job

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_knowledge_book_partial_generation_and_retry(monkeypatch):
    async with TestingSessionLocal() as db:
        user = User(email="author@test.com", password_hash="hash", full_name="Author")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Mock the AI generation functions
        async def mock_generate_outline(*args, **kwargs):
            return {
                "title": "Book Title",
                "chapters": [
                    {"title": "Ch 1", "order": 1, "learning_objectives": [], "sections": []},
                    {"title": "Ch 2", "order": 2, "learning_objectives": [], "sections": []}
                ]
            }
            
        call_count = {"ch1": 0, "ch2": 0}
        
        async def mock_generate_chapter_content(topic, chapter_title, *args, **kwargs):
            if chapter_title == "Ch 1":
                call_count["ch1"] += 1
                return "# Chapter 1\n\nThis is chapter 1" + " x" * 150
            elif chapter_title == "Ch 2":
                call_count["ch2"] += 1
                if call_count["ch2"] == 1:
                    raise Exception("Random AI Failure")
                return "# Chapter 2\n\nThis is chapter 2" + " x" * 150
                
        def mock_convert_markdown_to_pdf(*args, **kwargs):
            return True

        monkeypatch.setattr("app.worker.handlers.book_handler.generate_outline", mock_generate_outline)
        monkeypatch.setattr("app.worker.handlers.book_handler.generate_chapter_content", mock_generate_chapter_content)
        monkeypatch.setattr("app.worker.handlers.book_handler.convert_markdown_to_pdf", mock_convert_markdown_to_pdf)
        
        async def mock_process_document(*args, **kwargs):
            return None
        monkeypatch.setattr("app.rag.orchestrator.rag_orchestrator.process_document", mock_process_document)

        from app.worker.manager import job_manager as manager
        
        # Setup internal safe process patch for testing
        async def _mock_process_job_safe(job_id):
            async with TestingSessionLocal() as session:
                job = await manager.update_job(session, job_id, status="processing", progress=0)
                try:
                    if job.job_type == "knowledge_book":
                        await process_knowledge_book_job(job_id, session, job.parameters)
                    elif job.job_type == "knowledge_chapter_retry":
                        await process_chapter_retry_job(job_id, session, job.parameters)
                except Exception as e:
                    await manager.update_job(session, job_id, status="failed", error=str(e))
                    
        manager._process_job_safe = _mock_process_job_safe

        # Create book
        book = KnowledgeBook(
            user_id=user.id,
            title="Knowledge Book: Test",
            topic="Test",
            status="queued"
        )
        db.add(book)
        await db.commit()
        await db.refresh(book)
        
        user_id = user.id
        
        # Trigger Job 1: Book Generation
        job1 = await manager.create_job(
            db, user_id=user_id, job_type="knowledge_book",
            parameters={"book_id": book.id}, idempotency_key="b1"
        )
        
        await asyncio.sleep(0.5)
        
        book_id = book.id
        db.expire_all()
        res = await db.execute(select(KnowledgeBook).where(KnowledgeBook.id == book_id))
        book_after_1 = res.scalar_one()
        
        # Since Chapter 2 failed on first try, book should be failed
        assert book_after_1.status == "failed"
        
        res_ch = await db.execute(select(KnowledgeChapter).where(KnowledgeChapter.book_id == book_id).order_by(KnowledgeChapter.order))
        chapters = res_ch.scalars().all()
        assert len(chapters) == 2
        assert chapters[0].status == "completed"
        assert chapters[1].status == "failed"
        
        chapter_2_id = chapters[1].id
        
        # Trigger Job 2: Retry Chapter 2
        job2 = await manager.create_job(
            db, user_id=user_id, job_type="knowledge_chapter_retry",
            parameters={"chapter_id": chapter_2_id, "book_id": book_id}
        )
        
        await asyncio.sleep(1.0)
        
        db.expire_all()
        res = await db.execute(select(KnowledgeBook).where(KnowledgeBook.id == book_id))
        book_after_retry = res.scalar_one()
        
        res_ch = await db.execute(select(KnowledgeChapter).where(KnowledgeChapter.book_id == book_id).order_by(KnowledgeChapter.order))
        chapters_after = res_ch.scalars().all()
        
        # Both chapters should now be completed
        assert chapters_after[0].status == "completed"
        assert chapters_after[1].status == "completed"
        
        # The retry job should have resumed book generation, finishing the book
        assert book_after_retry.status == "completed"
        assert book_after_retry.progress == 100
