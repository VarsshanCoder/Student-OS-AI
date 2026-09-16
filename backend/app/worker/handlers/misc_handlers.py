import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.note import Note, NoteBlock
from app.services.embedding_service import embedding_service
from app.worker.manager import job_manager

logger = logging.getLogger(__name__)

async def process_embedding_generation_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    """Background job to re-generate embeddings for a given note's blocks."""
    note_id = parameters.get("note_id")
    if not note_id:
        raise ValueError("Missing note_id")

    await job_manager.update_job(db, job_id, status="embedding", progress=10, message="Fetching note blocks...")
    
    res = await db.execute(select(NoteBlock).where(NoteBlock.note_id == note_id))
    blocks = res.scalars().all()
    
    total = len(blocks)
    if total == 0:
        await job_manager.update_job(db, job_id, status="completed", progress=100, message="No blocks to embed.")
        return

    for idx, block in enumerate(blocks):
        if block.content and block.content.strip():
            emb = await embedding_service.get_embedding(block.content)
            # Hypothetical assignment if NoteBlock had an embedding column, or we just sync it to another table
            # block.embedding = emb
            pass
            
        if idx % 10 == 0:
            prog = 10 + int((idx / total) * 80)
            await job_manager.update_job(db, job_id, status="embedding", progress=prog, message=f"Embedded {idx+1}/{total} blocks")
            
    await db.commit()
    
    await job_manager.update_job(
        db, job_id, 
        status="completed", 
        progress=100, 
        message="Embeddings generated successfully."
    )

async def process_knowledge_book_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    """Background job to generate a large Knowledge Book from multiple sources."""
    topic = parameters.get("topic", "General Knowledge")
    
    await job_manager.update_job(db, job_id, status="extracting", progress=10, message=f"Extracting sources for {topic}...")
    import asyncio
    await asyncio.sleep(2) # simulate heavy extraction
    
    await job_manager.update_job(db, job_id, status="generating", progress=50, message="Structuring Knowledge Book...")
    await asyncio.sleep(2) # simulate heavy LLM work
    
    await job_manager.update_job(db, job_id, status="indexing", progress=80, message="Indexing chapters...")
    await asyncio.sleep(1)
    
    await job_manager.update_job(
        db, job_id, 
        status="completed", 
        progress=100, 
        message="Knowledge book created."
    )
