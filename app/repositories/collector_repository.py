import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.collector_session import CollectorSession


class CollectorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str | None = None) -> CollectorSession:
        session = CollectorSession(user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get(self, collector_session_id: int) -> CollectorSession | None:
        return self.db.get(CollectorSession, collector_session_id)

    def update_payload(
        self,
        session: CollectorSession,
        payload: Dict[str, Any],
        current_field: str,
        status: str,
        user_id: str | None = None,
    ):
        session.payload_json = json.dumps(payload)
        session.current_field = current_field
        session.status = status
        if user_id is not None:
            session.user_id = user_id
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

    @staticmethod
    def parse_payload(session: CollectorSession) -> Dict[str, Any]:
        return json.loads(session.payload_json)
