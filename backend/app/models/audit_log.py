from sqlalchemy import String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any
from datetime import datetime
from app.core.database import Base
from app.models.base import TimestampMixin

class AdminAuditLog(Base, TimestampMixin):
    __tablename__ = "admin_audit_logs"

    admin_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # USER_VIEWED, USER_SUSPENDED, USER_RESTORED, USER_DELETED, USER_PASSWORD_RESET, ROLE_CHANGED, DATA_EXPORTED
    target_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSON, default=dict, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    admin = relationship("User", foreign_keys=[admin_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
