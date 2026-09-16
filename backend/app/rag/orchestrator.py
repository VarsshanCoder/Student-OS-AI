import logging
import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.parser import document_parser
from app.rag.chunker import document_chunker
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class RAGOrchestrator:
    """
    Coordinates the ingestion of documents into the RAG pipeline.
    """
    
    async def process_document(
        self,
        db: AsyncSession,
        user_id: str,
        filename: str,
        file_bytes: bytes,
        subject_id: Optional[str] = None
    ) -> Document:
        """
        Complete pipeline: PDF -> Document Record -> Extract -> Chunk -> Embed -> PostgreSQL.
        """
        # 1. Create initial document record
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size_kb = len(file_bytes) // 1024
        
        doc = Document(
            user_id=user_id,
            subject_id=subject_id,
            filename=filename,
            file_size=f"{file_size_kb} KB",
            status="processing",
            content_hash=content_hash,
            version=1
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        try:
            # 2. Try Rust Scholar Engine First
            from app.rag.scholar_engine_client import scholar_engine_client
            engine_result = await scholar_engine_client.process_document(str(doc.id), file_bytes)
            
            if engine_result and "chunks" in engine_result:
                # Engine succeeded
                doc.page_count = engine_result.get("metadata", {}).get("page_count", 0)
                chunks_data = engine_result["chunks"]
            else:
                # 2b. Fallback to Python pipeline
                logger.info("Falling back to Python document processing pipeline")
                pages_data = document_parser.extract_text_from_pdf(file_bytes)
                doc.page_count = len(pages_data)
                chunks_data = document_chunker.chunk_paginated_text(pages_data)
            
            # 4. Embed and store chunks
            for chunk_data in chunks_data:
                embedding_vec = await embedding_service.get_embedding(chunk_data["content"])
                
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_data["chunk_index"],
                    page_number=chunk_data.get("page_number"),
                    content=chunk_data["content"],
                    embedding=embedding_vec
                )
                db.add(db_chunk)
                
            # 5. Mark as completed
            doc.status = "completed"
            await db.commit()
            await db.refresh(doc)
            return doc
            
        except Exception as e:
            logger.error(f"Failed to process document {doc.id}: {e}")
            doc.status = "failed"
            await db.commit()
            raise e
            
rag_orchestrator = RAGOrchestrator()
