import json
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.interview import Interview
from app.schemas.interview import InterviewSetupPayload


class InterviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: InterviewSetupPayload, questions: List[str], user_id: str | None = None) -> Interview:
        interview = Interview(
            user_id=user_id or payload.user_id,
            role=payload.role,
            interview_type=payload.interview_type,
            level=payload.level,
            techstack_csv=",".join(payload.techstack),
            amount=payload.amount,
            questions_json=json.dumps(questions),
        )
        self.db.add(interview)
        self.db.commit()
        self.db.refresh(interview)
        return interview

    def list_all(self, user_id: str | None = None) -> List[Interview]:
        stmt = select(Interview)
        if user_id:
            stmt = stmt.where(Interview.user_id == user_id)
        stmt = stmt.order_by(Interview.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, interview_id: int, user_id: str | None = None) -> Interview | None:
        interview = self.db.get(Interview, interview_id)
        if not interview:
            return None
        if user_id and interview.user_id and interview.user_id != user_id:
            return None
        return interview

    @staticmethod
    def parse_questions(interview: Interview) -> List[str]:
        return json.loads(interview.questions_json)

    @staticmethod
    def parse_techstack(interview: Interview) -> List[str]:
        return [item.strip() for item in interview.techstack_csv.split(",") if item.strip()]
