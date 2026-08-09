from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.core.database import Base
from app.models.base import TimestampMixin

class ResourceShare(Base, TimestampMixin):
    __tablename__ = "resource_shares"

    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("connect_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False) # note, pdf, flashcard, mindmap, quiz, study_plan
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(20), default="view_only", nullable=False) # view_only, can_duplicate, can_collaborate

    owner = relationship("User", foreign_keys=[owner_id])
    shared_with = relationship("User", foreign_keys=[shared_with_id])
    group = relationship("ConnectGroup", foreign_keys=[group_id])
