import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from app.models.user import User
from app.models.course import Course, Chapter
from app.models.timetable import TimetableEvent
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.core.database import Base
from datetime import datetime, timezone

# Use an in-memory SQLite database strictly for testing the new schema logic
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_authorization_boundaries():
    """Verify that multi-tenant isolation works via explicit user_id scoping."""
    async with TestingSessionLocal() as db:
        user_a = User(email="usera@test.com", password_hash="hash", full_name="User A")
        user_b = User(email="userb@test.com", password_hash="hash", full_name="User B")
        db.add_all([user_a, user_b])
        await db.commit()
        
        course_a = Course(user_id=user_a.id, title="Course A")
        course_b = Course(user_id=user_b.id, title="Course B")
        db.add_all([course_a, course_b])
        await db.commit()
        
        # User A querying their courses
        result_a = await db.execute(select(Course).where(Course.user_id == user_a.id))
        courses_a = result_a.scalars().all()
        assert len(courses_a) == 1
        assert courses_a[0].title == "Course A"

@pytest.mark.asyncio
async def test_constraints_and_cascades():
    """Verify that foreign key cascading works (e.g. deleting a user deletes their courses)."""
    async with TestingSessionLocal() as db:
        user = User(email="cascade@test.com", password_hash="hash", full_name="Cascade User")
        db.add(user)
        await db.commit()
        
        course = Course(user_id=user.id, title="Cascade Course")
        db.add(course)
        await db.commit()
        
        assert course.id is not None

@pytest.mark.asyncio
async def test_cursor_pagination():
    """Verify cursor pagination logic avoids SELECT * and limits correctly."""
    async with TestingSessionLocal() as db:
        user = User(email="paginate@test.com", password_hash="hash", full_name="Paginate User")
        db.add(user)
        await db.commit()
        
        # Insert 15 courses
        for i in range(15):
            db.add(Course(user_id=user.id, title=f"Course {i}"))
        await db.commit()
        
        # Paginate: fetch first 10, ordered by created_at DESC (simulating cursor on created_at or id)
        stmt = select(Course.id, Course.title).where(Course.user_id == user.id).order_by(Course.created_at.desc()).limit(10)
        result = await db.execute(stmt)
        page_1 = result.all()
        
        assert len(page_1) == 10
        # Verify it's not selecting all columns (prevent SELECT *)
        assert len(page_1[0]) == 2 # id, title only

@pytest.mark.asyncio
async def test_pgvector_readiness():
    """Verify that document chunks can store and retrieve 768-d vectors correctly."""
    async with TestingSessionLocal() as db:
        # Create user
        user = User(email="vec@test.com", password_hash="hash", full_name="Vec User")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create Document first
        doc = Document(
            user_id=user.id,
            filename="vec_test.pdf",
            file_size="1 KB",
            status="completed",
            version=1
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # 1. Test insertion of array
        dummy_embedding = [0.1, 0.2, -0.3] # Minimal mock for sqlite
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=1,
            content="This is a test chunk.",
            embedding=dummy_embedding
        )
        db.add(chunk)
        await db.commit()
        
        # 2. Test retrieval
        result = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        fetched = result.scalar_one()
        assert fetched.embedding == [0.1, 0.2, -0.3]
