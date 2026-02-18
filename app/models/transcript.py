from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TranscriptEntry(Base):
    __tablename__ = "transcript_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_type: Mapped[str] = mapped_column(String(30), nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    speaker: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
