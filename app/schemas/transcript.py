from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TranscriptItem(BaseModel):
    id: int
    session_type: str
    session_id: int
    user_id: Optional[str] = None
    speaker: str
    message: str
    created_at: datetime


class TranscriptListResponse(BaseModel):
    user_id: Optional[str] = None
    items: List[TranscriptItem]


class VoiceTranscribeResponse(BaseModel):
    text: str
    user_id: Optional[str] = None
