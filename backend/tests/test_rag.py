import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, event
from sqlalchemy.engine import Engine
from app.core.database import Base
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.orchestrator import rag_orchestrator
from app.rag.retriever import document_retriever

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def sample_user():
    async with TestingSessionLocal() as db:
        user = User(email="rag_test@test.com", password_hash="hash", full_name="RAG User")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

@pytest.fixture
async def sample_user_2():
    async with TestingSessionLocal() as db:
        user = User(email="rag_test2@test.com", password_hash="hash", full_name="RAG User 2")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

@pytest.mark.asyncio
async def test_document_pipeline_upload_and_chunk(sample_user):
    """Test PDF upload orchestrates parsing, chunking, embedding, and saving."""
    dummy_pdf_bytes = b"dummy_pdf_content"
    
    with patch("app.rag.parser.document_parser.extract_text_from_pdf") as mock_extract:
        # Mock 2 pages of extracted text
        mock_extract.return_value = [
            {"page_number": 1, "text": "Page 1 Content\n\nParagraph 2"},
            {"page_number": 2, "text": "Page 2 Content"}
        ]
        
        async with TestingSessionLocal() as db:
            doc = await rag_orchestrator.process_document(
                db, 
                user_id=sample_user.id, 
                filename="test.pdf", 
                file_bytes=dummy_pdf_bytes
            )
            
            # Verify document record
            assert doc.status == "completed"
            assert doc.page_count == 2
            assert doc.version == 1
            
            # Verify chunks were created
            res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            chunks = res.scalars().all()
            
            assert len(chunks) == 2 # Both paras fit in chunk 1, page 2 is chunk 2
            assert chunks[0].page_number == 1
            assert chunks[1].page_number == 2

@pytest.mark.asyncio
async def test_retrieval_authorization_and_ownership(sample_user, sample_user_2):
    """Test that users cannot retrieve documents they don't own."""
    dummy_pdf_bytes = b"dummy"
    
    with patch("app.rag.parser.document_parser.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = [{"page_number": 1, "text": "Top secret content"}]
        
        async with TestingSessionLocal() as db:
            # User 1 uploads document
            await rag_orchestrator.process_document(db, sample_user.id, "secret.pdf", dummy_pdf_bytes)
            
            # User 1 searches
            chunks_1 = await document_retriever.retrieve(db, sample_user.id, "secret")
            assert len(chunks_1) == 1
            assert "Top secret" in chunks_1[0]["content"]
            
            # User 2 searches (SHOULD NOT FIND IT)
            chunks_2 = await document_retriever.retrieve(db, sample_user_2.id, "secret")
            assert len(chunks_2) == 0

@pytest.mark.asyncio
async def test_context_compression():
    """Test context filtering and citation generation."""
    chunks = [
        {"filename": "Bio101.pdf", "page_number": 5, "chunk_index": 2, "content": "Mitochondria is the powerhouse."},
        {"filename": "Bio101.pdf", "page_number": 6, "chunk_index": 3, "content": "ATP is energy."}
    ]
    
    compressed = document_retriever.compress_context(chunks)
    assert "RELEVANT KNOWLEDGE BASE SECTIONS:" in compressed
    assert "[Bio101.pdf - Page 5, Section 2]" in compressed
    assert "Mitochondria is the powerhouse." in compressed
    assert "[Bio101.pdf - Page 6, Section 3]" in compressed

@pytest.mark.asyncio
async def test_document_deletion_cascade(sample_user):
    """Test that deleting a document cascades and removes all chunks."""
    dummy_pdf_bytes = b"dummy"
    
    with patch("app.rag.parser.document_parser.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = [{"page_number": 1, "text": "Content"}]
        
        async with TestingSessionLocal() as db:
            doc = await rag_orchestrator.process_document(db, sample_user.id, "del.pdf", dummy_pdf_bytes)
            
            # Verify exists
            res = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            assert len(res.scalars().all()) == 1
            
            # Delete doc
            await db.delete(doc)
            await db.commit()
            
            # Verify chunks are cascaded
            res2 = await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            assert len(res2.scalars().all()) == 0
