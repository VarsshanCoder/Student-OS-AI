from sqlalchemy import String, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any
from app.core.database import Base
from app.models.base import TimestampMixin

class AsyncJob(Base, TimestampMixin):
    __tablename__ = "async_jobs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # E.g., 'pdf_processing', 'knowledge_book', 'large_note', 'embedding_generation'
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # 'queued', 'processing', 'extracting', 'chunking', 'embedding', 'indexing', 'generating', 'validating', 'completed', 'failed'
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Input / Output
    parameters: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    # Used for idempotency
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    
    # Error tracking
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User")
