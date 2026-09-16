from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.rag.orchestrator import rag_orchestrator
from app.rag.retriever import document_retriever
from sqlalchemy import select

router = APIRouter()

import os
import aiofiles
from app.worker.manager import job_manager

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    subject_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    file_bytes = await file.read()
    
    # 1. Create Document DB entry
    doc = Document(
        user_id=current_user.id,
        subject_id=subject_id,
        filename=file.filename,
        file_size=f"{len(file_bytes) / 1024:.1f} KB",
        status="queued",
        page_count=0
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # 2. Save file temporarily
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{doc.id}.pdf"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)
        
    # 3. Create Async Job
    job = await job_manager.create_job(
        db=db,
        user_id=current_user.id,
        job_type="pdf_processing",
        parameters={
            "document_id": doc.id,
            "file_path": file_path
        },
        idempotency_key=f"pdf_{doc.id}"
    )
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "page_count": doc.page_count,
        "job_id": job.id
    }

@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return res.scalars().all()

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == current_user.id)
    )
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    await db.delete(doc)
    await db.commit()
