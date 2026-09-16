from sqlalchemy import String, Integer, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from app.core.database import Base
from app.models.base import TimestampMixin

class AIRequest(Base, TimestampMixin):
    __tablename__ = "ai_requests"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", index=True)

class AIUsage(Base, TimestampMixin):
    __tablename__ = "ai_usage"
    
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    billing_period: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

class AICache(Base, TimestampMixin):
    __tablename__ = "ai_cache"
    
    # Exact caching fields
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    response: Mapped[Any] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    
    # Semantic caching fields
    task_category: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    normalized_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Vector embedding for semantic search (JSON in SQLite, cast to Vector in Postgres)
    embedding: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    # Privacy / Isolation
    is_personalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
