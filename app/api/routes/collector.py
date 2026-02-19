import base64

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


def process_collector_turn(
    collector_session_id: int,
    user_message: str,
    db: Session,
    user_id: str | None = None,
    openai_service: OpenAIService | None = None,
) -> CollectorTurnResponse:
    collector_repo = CollectorRepository(db)
    interview_repo = InterviewRepository(db)
    transcript_repo = TranscriptRepository(db)
    openai_service = openai_service or OpenAIService()

    session = collector_repo.get(collector_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collector session not found")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Collector session already completed")

    effective_user_id = user_id or session.user_id
    payload = collector_repo.parse_payload(session)
    current_field = session.current_field

    transcript_repo.add("collector", session.id, "user", user_message, user_id=effective_user_id)

    correction = InterviewFlowService.detect_correction(current_field, payload, user_message)
    if correction:
        target_field, corrected_text = correction
        try:
            corrected_value = InterviewFlowService.normalize_field_value(target_field, corrected_text)
        except ValueError as exc:
            msg = f"Got it. I couldn’t update {target_field} yet: {exc}"
            assistant_audio_base64 = None
            assistant_audio_content_type = None
            try:
                assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(msg)
                assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
            except Exception:
                assistant_audio_base64 = None
                assistant_audio_content_type = None
            transcript_repo.add("collector", session.id, "assistant", msg, user_id=effective_user_id)
            return CollectorTurnResponse(
                collector_session_id=session.id,
                user_id=effective_user_id,
                assistant_message=msg,
                assistant_audio_base64=assistant_audio_base64,
                assistant_audio_content_type=assistant_audio_content_type,
                expected_field=current_field,
                completed=False,
            )

        payload[target_field] = corrected_value
        collector_repo.update_payload(
            session,
            payload,
            current_field=current_field,
            status="collecting",
            user_id=effective_user_id,
        )

        if isinstance(corrected_value, list):
            corrected_display = ", ".join(corrected_value)
        else:
            corrected_display = str(corrected_value)

        assistant_message = (
            f"Understood, {corrected_display} it is. {FIELD_PROMPTS[current_field]}"
            if current_field in FIELD_PROMPTS
            else f"Understood, {corrected_display} it is."
        )

        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None

        transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=assistant_message,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
            expected_field=current_field,
            completed=False,
        )

    intent = InterviewFlowService.detect_turn_intent(current_field, user_message)
    if intent in {"repeat", "examples", "clarify", "clarify_readiness", "not_ready"}:
        assistant_message = InterviewFlowService.build_intent_reply(current_field, intent)
        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None
        transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=assistant_message,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
            expected_field=current_field,
            completed=False,
        )

    if current_field == "readiness" and intent != "confirm_ready":
        assistant_message = InterviewFlowService.build_intent_reply(current_field, "clarify_readiness")
        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None
        transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=assistant_message,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
            expected_field=current_field,
            completed=False,
        )

    try:
        normalized_value = InterviewFlowService.normalize_field_value(current_field, user_message)
    except ValueError as exc:
        msg = f"Thanks. I need a valid value for {current_field}: {exc}"
        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(msg)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None
        transcript_repo.add("collector", session.id, "assistant", msg, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=msg,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
            expected_field=current_field,
            completed=False,
        )
    except Exception:
        msg = f"Thanks. Could you provide {current_field} in a clear format?"
        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(msg)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None
        transcript_repo.add("collector", session.id, "assistant", msg, user_id=effective_user_id)
        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=msg,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
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
            user_response=user_message,
            next_field_prompt=(
                f"Perfect. I generated your interview and saved it to your dashboard. "
                f"You can now start interview #{interview.id}."
            ),
        )
        assistant_audio_base64 = None
        assistant_audio_content_type = None
        try:
            assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
            assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
        except Exception:
            assistant_audio_base64 = None
            assistant_audio_content_type = None
        transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)

        return CollectorTurnResponse(
            collector_session_id=session.id,
            user_id=effective_user_id,
            assistant_message=assistant_message,
            assistant_audio_base64=assistant_audio_base64,
            assistant_audio_content_type=assistant_audio_content_type,
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
        user_response=user_message,
        next_field_prompt=FIELD_PROMPTS[next_field],
    )
    assistant_audio_base64 = None
    assistant_audio_content_type = None
    try:
        assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
        assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
    except Exception:
        assistant_audio_base64 = None
        assistant_audio_content_type = None
    transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=effective_user_id)

    return CollectorTurnResponse(
        collector_session_id=session.id,
        user_id=effective_user_id,
        assistant_message=assistant_message,
        assistant_audio_base64=assistant_audio_base64,
        assistant_audio_content_type=assistant_audio_content_type,
        expected_field=next_field,
        completed=False,
    )


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

    payload = {}
    if body and body.candidate_name:
        payload["candidate_name"] = body.candidate_name
    collector_repo.update_payload(session, payload, current_field="readiness", status="collecting", user_id=session.user_id)

    assistant_message = InterviewFlowService.build_opening_prompt(body.candidate_name if body else None)
    assistant_audio_base64 = None
    assistant_audio_content_type = None
    try:
        openai_service = OpenAIService()
        assistant_audio, assistant_audio_content_type = openai_service.synthesize_speech(assistant_message)
        assistant_audio_base64 = base64.b64encode(assistant_audio).decode("utf-8")
    except Exception:
        assistant_audio_base64 = None
        assistant_audio_content_type = None

    transcript_repo = TranscriptRepository(db)
    transcript_repo.add("collector", session.id, "assistant", assistant_message, user_id=session.user_id)

    return CollectorStartResponse(
        collector_session_id=session.id,
        user_id=session.user_id,
        assistant_message=assistant_message,
        assistant_audio_base64=assistant_audio_base64,
        assistant_audio_content_type=assistant_audio_content_type,
        expected_field="readiness",
    )


@router.post("/{collector_session_id}/turn", response_model=CollectorTurnResponse)
def collector_turn(
    collector_session_id: int,
    body: CollectorTurnRequest,
    db: Session = Depends(get_db),
):
    return process_collector_turn(
        collector_session_id=collector_session_id,
        user_message=body.user_message,
        user_id=body.user_id,
        db=db,
        openai_service=OpenAIService(),
    )
