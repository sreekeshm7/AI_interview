from typing import Optional

from pydantic import BaseModel, Field


class CollectorStartResponse(BaseModel):
    collector_session_id: int
    user_id: Optional[str] = None
    assistant_message: str
    expected_field: str


class CollectorStartRequest(BaseModel):
    user_id: Optional[str] = None


class CollectorTurnRequest(BaseModel):
    user_message: str = Field(min_length=1)
    user_id: Optional[str] = None


class CollectorTurnResponse(BaseModel):
    collector_session_id: int
    user_id: Optional[str] = None
    assistant_message: str
    expected_field: Optional[str] = None
    completed: bool = False
    interview_id: Optional[int] = None
