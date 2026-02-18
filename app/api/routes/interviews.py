from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.cache import interview_cache
from app.db.session import get_db
from app.repositories.interview_repository import InterviewRepository
from app.repositories.interview_session_repository import InterviewSessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.interview import (
    InterviewCreateResponse,
    InterviewListItem,
    InterviewSessionStartRequest,
    InterviewSessionStartResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
)
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.get("", response_model=list[InterviewListItem])
def list_interviews(user_id: str | None = None, db: Session = Depends(get_db)):
    repo = InterviewRepository(db)
    interviews = repo.list_all(user_id=user_id)

    return [
        InterviewListItem(
            id=item.id,
            user_id=item.user_id,
            role=item.role,
            interview_type=item.interview_type,
            level=item.level,
            techstack=repo.parse_techstack(item),
            amount=item.amount,
            created_at=item.created_at,
        )
        for item in interviews
    ]


@router.get("/{interview_id}", response_model=InterviewCreateResponse)
def get_interview(interview_id: int, user_id: str | None = None, db: Session = Depends(get_db)):
    repo = InterviewRepository(db)
    interview = repo.get_by_id(interview_id, user_id=user_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = interview_cache.get_interview_questions(interview.id)
    if not questions:
        questions = repo.parse_questions(interview)
        interview_cache.set_interview_questions(interview.id, questions)

    return InterviewCreateResponse(interview_id=interview.id, user_id=interview.user_id, questions=questions)


@router.post("/{interview_id}/start", response_model=InterviewSessionStartResponse)
def start_interview(
    interview_id: int,
    body: InterviewSessionStartRequest | None = None,
    db: Session = Depends(get_db),
):
    interview_repo = InterviewRepository(db)
    session_repo = InterviewSessionRepository(db)
    transcript_repo = TranscriptRepository(db)
    requested_user_id = body.user_id if body else None

    interview = interview_repo.get_by_id(interview_id, user_id=requested_user_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = interview_cache.get_interview_questions(interview.id)
    if not questions:
        questions = interview_repo.parse_questions(interview)
        interview_cache.set_interview_questions(interview.id, questions)
    if not questions:
        raise HTTPException(status_code=400, detail="Interview has no questions")

    effective_user_id = requested_user_id or interview.user_id
    interview_session = session_repo.create(interview_id, user_id=effective_user_id)
    interview_cache.set_session_questions(interview_session.id, questions)
    assistant_message = f"Great, let’s begin. First question: {questions[0]}"
    transcript_repo.add("interview", interview_session.id, "assistant", assistant_message, user_id=effective_user_id)

    return InterviewSessionStartResponse(
        interview_session_id=interview_session.id,
        user_id=effective_user_id,
        assistant_message=assistant_message,
        question_index=0,
    )


@router.post("/sessions/{interview_session_id}/turn", response_model=InterviewTurnResponse)
def interview_turn(
    interview_session_id: int,
    body: InterviewTurnRequest,
    db: Session = Depends(get_db),
):
    interview_repo = InterviewRepository(db)
    session_repo = InterviewSessionRepository(db)
    transcript_repo = TranscriptRepository(db)
    openai_service = OpenAIService()

    interview_session = session_repo.get(interview_session_id, user_id=body.user_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if interview_session.status == "completed":
        raise HTTPException(status_code=400, detail="Interview session already completed")
    effective_user_id = body.user_id or interview_session.user_id

    interview = interview_repo.get_by_id(interview_session.interview_id, user_id=effective_user_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = interview_cache.get_session_questions(interview_session.id)
    if not questions:
        questions = interview_cache.get_interview_questions(interview.id)
    if not questions:
        questions = interview_repo.parse_questions(interview)
        interview_cache.set_interview_questions(interview.id, questions)
    interview_cache.set_session_questions(interview_session.id, questions)

    idx = interview_session.current_index
    if idx >= len(questions):
        interview_session.status = "completed"
        session_repo.save(interview_session)
        interview_cache.clear_session(interview_session.id)
        raise HTTPException(status_code=400, detail="Interview already completed")

    transcript_repo.add("interview", interview_session.id, "user", body.user_message, user_id=effective_user_id)

    current_question = questions[idx]
    next_idx = idx + 1
    next_question = questions[next_idx] if next_idx < len(questions) else None

    assistant_message = openai_service.build_interview_turn_reply(
        user_answer=body.user_message,
        current_question=current_question,
        next_question=next_question,
    )

    if next_question is None:
        interview_session.current_index = len(questions)
        interview_session.status = "completed"
        session_repo.save(interview_session)
        interview_cache.clear_session(interview_session.id)
        status = "completed"
        returned_index = None
    else:
        interview_session.current_index = next_idx
        session_repo.save(interview_session)
        status = "active"
        returned_index = next_idx

    transcript_repo.add("interview", interview_session.id, "assistant", assistant_message, user_id=effective_user_id)

    return InterviewTurnResponse(
        interview_session_id=interview_session.id,
        user_id=effective_user_id,
        assistant_message=assistant_message,
        status=status,
        question_index=returned_index,
    )
