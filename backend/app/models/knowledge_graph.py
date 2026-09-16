from sqlalchemy import String, Integer, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from app.core.database import Base
from app.models.base import TimestampMixin

class KnowledgeNode(Base, TimestampMixin):
    __tablename__ = "knowledge_nodes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)

class KnowledgeEdge(Base, TimestampMixin):
    __tablename__ = "knowledge_edges"

    source_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., 'prerequisite', 'related'
    weight: Mapped[float] = mapped_column(Float, default=1.0)
