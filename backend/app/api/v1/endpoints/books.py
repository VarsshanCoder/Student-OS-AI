from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
import hashlib

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.knowledge_book import KnowledgeBook, KnowledgeChapter
from app.worker.manager import job_manager

router = APIRouter()

class KnowledgeBookCreate(BaseModel):
    topic: str
    level: Optional[str] = "college-level"
    language: Optional[str] = "en"
    style: Optional[str] = "detailed"
    target_length: Optional[str] = "medium"
    syllabus: Optional[str] = None
    document_ids: Optional[List[str]] = []

class KnowledgeBookResponse(BaseModel):
    id: str
    title: str
    topic: str
    status: str
    progress: int
    job_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class ChapterResponse(BaseModel):
    id: str
    title: str
    order: int
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class KnowledgeBookDetailResponse(KnowledgeBookResponse):
    chapters: List[ChapterResponse] = []

@router.post("/generate", response_model=KnowledgeBookResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_book(
    req: KnowledgeBookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Initialize the Book in DB
    book = KnowledgeBook(
        user_id=current_user.id,
        title=f"Knowledge Book: {req.topic}",
        topic=req.topic,
        level=req.level,
        language=req.language,
        style=req.style,
        target_length=req.target_length,
        status="queued",
        progress=0
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    
    # Idempotency key
    raw_key = f"{current_user.id}_book_{req.topic}_{req.level}_{req.language}"
    idemp_key = hashlib.sha256(raw_key.encode()).hexdigest()
    
    parameters = {
        "book_id": book.id,
        "topic": req.topic,
        "level": req.level,
        "language": req.language,
        "style": req.style,
        "target_length": req.target_length,
        "syllabus": req.syllabus,
        "document_ids": req.document_ids
    }
    
    job = await job_manager.create_job(
        db=db,
        user_id=current_user.id,
        job_type="knowledge_book",
        parameters=parameters,
        idempotency_key=idemp_key
    )
    
    book.job_id = job.id
    await db.commit()
    
    return book

@router.get("", response_model=List[KnowledgeBookResponse])
async def list_books(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(KnowledgeBook)
        .where(KnowledgeBook.user_id == current_user.id)
        .order_by(KnowledgeBook.created_at.desc())
    )
    return res.scalars().all()

@router.get("/{book_id}", response_model=KnowledgeBookDetailResponse)
async def get_book(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(KnowledgeBook)
        .options(selectinload(KnowledgeBook.chapters))
        .where(KnowledgeBook.id == book_id)
        .where(KnowledgeBook.user_id == current_user.id)
    )
    book = res.scalars().first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    return book

@router.post("/{book_id}/retry-chapter/{chapter_id}")
async def retry_chapter(
    book_id: str,
    chapter_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch chapter
    res = await db.execute(
        select(KnowledgeChapter)
        .where(KnowledgeChapter.id == chapter_id)
        .where(KnowledgeChapter.book_id == book_id)
    )
    chapter = res.scalars().first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
        
    if chapter.status not in ["failed", "completed"]:
        raise HTTPException(status_code=400, detail=f"Cannot retry chapter in status: {chapter.status}")
        
    chapter.status = "pending"
    chapter.error_message = None
    chapter.retry_count += 1
    
    # We will enqueue a specific chapter generation job
    job = await job_manager.create_job(
        db=db,
        user_id=current_user.id,
        job_type="knowledge_chapter_retry",
        parameters={"chapter_id": chapter.id, "book_id": book_id}
    )
    
    await db.commit()
    return {"status": "Chapter retry queued", "job_id": job.id}
