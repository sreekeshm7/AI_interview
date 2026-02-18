from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transcript import TranscriptEntry


class TranscriptRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        session_type: str,
        session_id: int,
        speaker: str,
        message: str,
        user_id: str | None = None,
    ) -> TranscriptEntry:
        entry = TranscriptEntry(
            session_type=session_type,
            session_id=session_id,
            user_id=user_id,
            speaker=speaker,
            message=message,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list(self, session_type: str, session_id: int, user_id: str | None = None) -> List[TranscriptEntry]:
        stmt = select(TranscriptEntry).where(
            TranscriptEntry.session_type == session_type,
            TranscriptEntry.session_id == session_id,
        )
        if user_id:
            stmt = stmt.where(TranscriptEntry.user_id == user_id)
        stmt = stmt.order_by(TranscriptEntry.created_at.asc())
        return list(self.db.scalars(stmt).all())
