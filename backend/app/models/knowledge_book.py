from sqlalchemy import String, Integer, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Any
from app.core.database import Base
from app.models.base import TimestampMixin

class KnowledgeBook(Base, TimestampMixin):
    __tablename__ = "knowledge_books"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    style: Mapped[str] = mapped_column(String(50), nullable=True)
    
    target_length: Mapped[str] = mapped_column(String(50), nullable=True)
    target_chapters: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Status: queued, outlining, generating_chapters, assembling, indexing, completed, failed
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    
    # Document output locations
    markdown_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Store the syllabus or outline definition
    outline_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    # To resume state if needed
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("async_jobs.id", ondelete="SET NULL"), nullable=True)
    
    chapters: Mapped[List["KnowledgeChapter"]] = relationship("KnowledgeChapter", back_populates="book", cascade="all, delete-orphan", order_by="KnowledgeChapter.order")


class KnowledgeChapter(Base, TimestampMixin):
    __tablename__ = "knowledge_chapters"

    book_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_books.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status: pending, generating, validating, completed, failed
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    
    # Outline schema for this specific chapter
    outline_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    book: Mapped["KnowledgeBook"] = relationship("KnowledgeBook", back_populates="chapters")
