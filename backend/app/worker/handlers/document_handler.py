import os
import aiofiles
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.job import AsyncJob
from app.rag.parser import document_parser
from app.rag.chunker import document_chunker
from app.services.embedding_service import embedding_service
from app.worker.manager import job_manager

logger = logging.getLogger(__name__)

async def process_pdf_job(job_id: str, db: AsyncSession, parameters: Dict[str, Any]):
    file_path = parameters.get("file_path")
    document_id = parameters.get("document_id")
    
    if not file_path or not document_id:
        raise ValueError("Missing file_path or document_id in job parameters")
        
    # Get the document
    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")
        
    try:
        # 1. Read file bytes
        await job_manager.update_job(db, job_id, status="extracting", progress=10)
        async with aiofiles.open(file_path, "rb") as f:
            file_bytes = await f.read()
            
        # 2. Try Rust Engine
        from app.rag.scholar_engine_client import scholar_engine_client
        engine_result = await scholar_engine_client.process_document(str(doc.id), file_bytes)
        
        await job_manager.update_job(db, job_id, status="chunking", progress=40)
        
        if engine_result and "chunks" in engine_result:
            doc.page_count = engine_result.get("metadata", {}).get("page_count", 0)
            chunks_data = engine_result["chunks"]
        else:
            # Fallback
            logger.info("Falling back to Python document processing pipeline")
            pages_data = document_parser.extract_text_from_pdf(file_bytes)
            doc.page_count = len(pages_data)
            chunks_data = document_chunker.chunk_paginated_text(pages_data)
            
        # 3. Embedding and Indexing
        await job_manager.update_job(db, job_id, status="embedding", progress=60)
        
        total_chunks = len(chunks_data)
        for idx, chunk_data in enumerate(chunks_data):
            embedding_vec = await embedding_service.get_embedding(chunk_data["content"])
            
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data.get("page_number"),
                content=chunk_data["content"],
                embedding=embedding_vec
            )
            db.add(db_chunk)
            
            # Update progress periodically
            if idx % 10 == 0:
                prog = 60 + int((idx / total_chunks) * 30)
                await job_manager.update_job(db, job_id, status="indexing", progress=prog)
                
        # Finalize Document
        doc.status = "completed"
        await db.commit()
        
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        await job_manager.update_job(
            db, job_id, 
            status="completed", 
            progress=100,
            result={"document_id": doc.id, "chunks_processed": total_chunks}
        )

    except Exception as e:
        doc.status = "failed"
        await db.commit()
        raise e
