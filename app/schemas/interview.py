from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InterviewSetupPayload(BaseModel):
    user_id: Optional[str] = None
    role: str = Field(min_length=1)
    interview_type: str = Field(min_length=1)
    level: str = Field(min_length=1)
    techstack: List[str] = Field(min_length=1)
    amount: int = Field(ge=1, le=30)


class InterviewCreateResponse(BaseModel):
    interview_id: int
    user_id: Optional[str] = None
    questions: List[str]


class InterviewListItem(BaseModel):
    id: int
    user_id: Optional[str] = None
    role: str
    interview_type: str
    level: str
    techstack: List[str]
    amount: int
    created_at: datetime


class InterviewSessionStartRequest(BaseModel):
    user_id: Optional[str] = None


class InterviewSessionStartResponse(BaseModel):
    interview_session_id: int
    user_id: Optional[str] = None
    assistant_message: str
    question_index: int


class InterviewTurnRequest(BaseModel):
    user_message: str = Field(min_length=1)
    user_id: Optional[str] = None


class InterviewTurnResponse(BaseModel):
    interview_session_id: int
    user_id: Optional[str] = None
    assistant_message: str
    status: str
    question_index: Optional[int] = None
