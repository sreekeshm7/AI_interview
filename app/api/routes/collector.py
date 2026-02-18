from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.cache import interview_cache
from app.db.session import get_db
from app.repositories.collector_repository import CollectorRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.schemas.collector import CollectorStartRequest, CollectorStartResponse, CollectorTurnRequest, CollectorTurnResponse
from app.services.interview_flow_service import FIELD_PROMPTS, InterviewFlowService
from app.services.openai_service import OpenAIService

router = APIRouter(prefix="/collector", tags=["collector"])


@router.post("/start", response_model=CollectorStartResponse)
def start_collector(body: CollectorStartRequest | None = None, db: Session = Depends(get_db)):
    try:
        collector_repo = CollectorRepository(db)
        user_id = body.user_id if body else None
        session = collector_repo.create(user_id=user_id)
    except Exception as exc:
        print(f"[collector/start] Error creating session: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create collector session: {str(exc)}")

    assistant_message = FIELD_PROMPTS["role"]

    transcript_repo = TranscriptRepository(db)
    transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=session.user_id)

    return CollectorStartResponse(
        collector_session_id=session.id,
        user_id=session.user_id,
        assistant_message=assistant_message,
        expected_field="role",
    )


@router.post("/{collector_session_id}/turn", response_model=CollectorTurnResponse)
def collector_turn(
    collector_session_id: int,
    body: CollectorTurnRequest,
    db: Session = Depends(get_db),
):
    collector_repo = CollectorRepository(db)
    interview_repo = InterviewRepository(db)
    transcript_repo = TranscriptRepository(db)
    openai_service = OpenAIService()

    session = collector_repo.get(collector_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collector session not found")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Collector session already completed")
    effective_user_id = body.user_id or session.user_id

    payload = collector_repo.parse_payload(session)
    current_field = session.current_field

    transcript_repo.add("collector", session.id, "user", body.user_message, user_id=effective_user_id)

    try:
        normalized_value = InterviewFlowService.normalize_field_value(current_field, body.user_message)
    except ValueError as exc:
        msg = f"Thanks. I need a valid value for {current_field}: {exc}"
        transcript_repo.add("collector", session.id, "assistant", msg, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=msg,
            expected_field=current_field,
            completed=False,
        )
    except Exception:
        msg = f"Thanks. Could you provide {current_field} in a clear format?"
        transcript_repo.add("collector", session.id, "assistant", msg, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=msg,
            expected_field=current_field,
            completed=False,
        )

    payload[current_field] = normalized_value
    progress = InterviewFlowService.get_next_field(current_field)

    if progress.completed:
        interview_payload = InterviewFlowService.build_payload(payload)
        interview_payload.user_id = effective_user_id
        questions = openai_service.generate_interview_questions(interview_payload)
        interview = interview_repo.create(interview_payload, questions, user_id=effective_user_id)
        interview_cache.set_interview_questions(interview.id, questions)

        collector_repo.update_payload(
            session,
            payload,
            current_field="amount",
            status="completed",
            user_id=effective_user_id,
        )

        assistant_message = openai_service.build_collector_reply(
            field_name=current_field,
            user_response=body.user_message,
            next_field_prompt=(
                f"Perfect. I generated your interview and saved it to your dashboard. "
                f"You can now start interview #{interview.id}."
            ),
        )
        transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)

        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=assistant_message,
            completed=True,
            interview_id=interview.id,
        )

    next_field = progress.next_field
    collector_repo.update_payload(
        session,
        payload,
        current_field=next_field,
        status="collecting",
        user_id=effective_user_id,
    )

    assistant_message = openai_service.build_collector_reply(
        field_name=current_field,
        user_response=body.user_message,
        next_field_prompt=FIELD_PROMPTS[next_field],
    )
    transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)

    return CollectorTurnResponse(
        collector_session_id=session.id,
        user_id=effective_user_id,
        assistant_message=assistant_message,
        expected_field=next_field,
        completed=False,
    )
