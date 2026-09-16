import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class DocumentRetriever:
    def __init__(self, default_top_k: int = 5, default_threshold: float = 0.75):
        self.default_top_k = default_top_k
        self.default_threshold = default_threshold

    async def retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        subject_id: Optional[str] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant chunks safely filtered by user_id.
        NEVER retrieves another student's documents.
        """
        k = top_k or self.default_top_k
        threshold = similarity_threshold or self.default_threshold
        
        query_vec = await embedding_service.get_embedding(query)
        bind = db.get_bind()
        
        # PostgreSQL with pgvector
        if bind.engine.name == 'postgresql':
            sql = """
                SELECT dc.content, dc.page_number, dc.chunk_index, d.filename, d.id as document_id,
                       1 - (dc.embedding <=> :query_vec::vector) AS similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.user_id = :user_id 
                  AND d.status = 'completed'
            """
            
            params = {
                "query_vec": str(query_vec),
                "user_id": user_id,
                "limit": k,
                "threshold": threshold
            }
            
            if subject_id:
                sql += " AND d.subject_id = :subject_id"
                params["subject_id"] = subject_id
                
            sql += """
                ORDER BY dc.embedding <=> :query_vec::vector
                LIMIT :limit
            """
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            chunks = []
            for r in rows:
                if float(r.similarity) >= threshold:
                    chunks.append({
                        "document_id": str(r.document_id),
                        "filename": r.filename,
                        "page_number": r.page_number,
                        "chunk_index": r.chunk_index,
                        "content": r.content,
                        "similarity": float(r.similarity)
                    })
            return chunks
        
        else:
            # Fallback for local SQLite testing: Just return all chunks up to k
            # WARNING: This does not do semantic filtering! It's just for local test isolation.
            sql = """
                SELECT dc.content, dc.page_number, dc.chunk_index, d.filename, d.id as document_id
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.user_id = :user_id
                  AND d.status = 'completed'
            """
            params = {"user_id": user_id, "limit": k}
            if subject_id:
                sql += " AND d.subject_id = :subject_id"
                params["subject_id"] = subject_id
                
            sql += " LIMIT :limit"
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            return [
                {
                    "document_id": str(r.document_id),
                    "filename": r.filename,
                    "page_number": r.page_number,
                    "chunk_index": r.chunk_index,
                    "content": r.content,
                    "similarity": 1.0 # Mock similarity
                }
                for r in rows
            ]

    def compress_context(self, chunks: List[Dict[str, Any]], max_chars: int = 12000) -> str:
        """
        Compresses retrieved chunks into a single context string with precise citations.
        """
        if not chunks:
            return ""
            
        context_str = "RELEVANT KNOWLEDGE BASE SECTIONS:\n\n"
        current_len = len(context_str)
        
        for chunk in chunks:
            citation = f"[{chunk['filename']} - Page {chunk['page_number'] or 'N/A'}, Section {chunk['chunk_index']}]"
            block = f"{citation}\n{chunk['content']}\n\n"
            
            if current_len + len(block) > max_chars:
                break
                
            context_str += block
            current_len += len(block)
            
        return context_str.strip()

document_retriever = DocumentRetriever()
