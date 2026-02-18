from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.transcript import TranscriptItem, TranscriptListResponse, VoiceTranscribeResponse
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/{session_type}/{session_id}", response_model=TranscriptListResponse)
def get_transcripts(
    session_type: str,
    session_id: int,
    user_id: str | None = None,
    db: Session = Depends(get_db),
):
    if session_type not in {"collector", "interview"}:
        raise HTTPException(status_code=400, detail="session_type must be collector or interview")

    repo = TranscriptRepository(db)
    entries = repo.list(session_type=session_type, session_id=session_id, user_id=user_id)
    return TranscriptListResponse(
        user_id=user_id,
        items=[
            TranscriptItem(
                id=entry.id,
                session_type=entry.session_type,
                session_id=entry.session_id,
                user_id=entry.user_id,
                speaker=entry.speaker,
                message=entry.message,
                created_at=entry.created_at,
            )
            for entry in entries
        ]
    )


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    audio_file: UploadFile = File(...),
    session_type: str | None = Form(default=None),
    session_id: int | None = Form(default=None),
    user_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    content = await audio_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="audio_file is empty")

    openai_service = OpenAIService()
    text = openai_service.transcribe_audio(audio_file.filename or "audio.wav", content)

    if session_type and session_id:
        if session_type not in {"collector", "interview"}:
            raise HTTPException(status_code=400, detail="session_type must be collector or interview")
        repo = TranscriptRepository(db)
        repo.add(session_type=session_type, session_id=session_id, speaker="user", message=text, user_id=user_id)

    return VoiceTranscribeResponse(text=text, user_id=user_id)
