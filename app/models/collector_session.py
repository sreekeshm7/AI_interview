from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CollectorSession(Base):
    __tablename__ = "collector_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="collecting", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    current_field: Mapped[str] = mapped_column(String(30), default="role", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
