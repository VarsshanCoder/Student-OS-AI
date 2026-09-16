from sqlalchemy import String, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any
from app.core.database import Base
from app.models.base import TimestampMixin

class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # We use JSON for local dev compatibility, Alembic will cast this to VECTOR(768) in production Postgres.
    embedding: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    metadata_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    document = relationship("Document")
