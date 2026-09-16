from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from app.core.database import Base
from app.models.base import TimestampMixin

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[str] = mapped_column(String(50), default="0 KB", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # State tracking
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User")
