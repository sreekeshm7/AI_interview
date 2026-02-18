from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview_session import InterviewSession


class InterviewSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, interview_id: int, user_id: str | None = None) -> InterviewSession:
        session = InterviewSession(interview_id=interview_id, user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get(self, interview_session_id: int, user_id: str | None = None) -> InterviewSession | None:
        session = self.db.get(InterviewSession, interview_session_id)
        if not session:
            return None
        if user_id and session.user_id and session.user_id != user_id:
            return None
        return session

    def save(self, session: InterviewSession):
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

    def list_by_interview_id(self, interview_id: int) -> list[InterviewSession]:
        stmt = select(InterviewSession).where(InterviewSession.interview_id == interview_id)
        return list(self.db.scalars(stmt).all())
