import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.cache import interview_cache
from app.db.session import SessionLocal
from app.repositories.interview_repository import InterviewRepository
from app.repositories.interview_session_repository import InterviewSessionRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.services.openai_service import OpenAIService

router = APIRouter(tags=["voice"])


@router.websocket("/interviews/sessions/{interview_session_id}/voice")
async def interview_voice_socket(websocket: WebSocket, interview_session_id: int):
    await websocket.accept()
    user_id = websocket.query_params.get("user_id")

    db = SessionLocal()
    openai_service = OpenAIService()

    try:
        interview_repo = InterviewRepository(db)
        session_repo = InterviewSessionRepository(db)
        transcript_repo = TranscriptRepository(db)

        interview_session = session_repo.get(interview_session_id, user_id=user_id)
        if not interview_session:
            await websocket.send_json({"type": "error", "message": "Interview session not found"})
            await websocket.close(code=1008)
            return

        interview = interview_repo.get_by_id(interview_session.interview_id, user_id=user_id)
        if not interview:
            await websocket.send_json({"type": "error", "message": "Interview not found"})
            await websocket.close(code=1008)
            return

        questions = interview_cache.get_session_questions(interview_session.id)
        if not questions:
            questions = interview_cache.get_interview_questions(interview.id)
        if not questions:
            questions = interview_repo.parse_questions(interview)
            interview_cache.set_interview_questions(interview.id, questions)
        interview_cache.set_session_questions(interview_session.id, questions)

        if not questions:
            await websocket.send_json({"type": "error", "message": "Interview has no questions"})
            await websocket.close(code=1008)
            return

        if interview_session.status == "completed" or interview_session.current_index >= len(questions):
            await websocket.send_json({"type": "completed", "message": "Interview already completed"})
            await websocket.close(code=1000)
            return

        current_index = interview_session.current_index
        if current_index == 0:
            prompt_text = f"Great, let’s begin. First question: {questions[current_index]}"
        else:
            prompt_text = f"Welcome back. Next question: {questions[current_index]}"

        entries = transcript_repo.list("interview", interview_session.id, user_id=user_id)
        if len(entries) == 0:
            transcript_repo.add(
                session_type="interview",
                session_id=interview_session.id,
                speaker="assistant",
                message=prompt_text,
                user_id=user_id,
            )

        opening_audio, opening_content_type = openai_service.synthesize_speech(prompt_text)
        await websocket.send_json(
            {
                "type": "assistant_prompt",
                "user_id": user_id,
                "interview_session_id": interview_session.id,
                "status": interview_session.status,
                "question_index": current_index,
                "assistant_text": prompt_text,
                "assistant_audio_base64": base64.b64encode(opening_audio).decode("utf-8"),
                "assistant_audio_content_type": opening_content_type,
            }
        )

        while True:
            incoming = await websocket.receive_text()
            try:
                payload = json.loads(incoming)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload"})
                continue

            event_type = payload.get("type")
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            interview_session = session_repo.get(interview_session_id, user_id=user_id)
            if not interview_session:
                await websocket.send_json({"type": "error", "message": "Interview session not found"})
                await websocket.close(code=1008)
                return

            if interview_session.status == "completed":
                await websocket.send_json({"type": "completed", "message": "Interview already completed"})
                continue

            current_index = interview_session.current_index
            if current_index >= len(questions):
                interview_session.status = "completed"
                session_repo.save(interview_session)
                interview_cache.clear_session(interview_session.id)
                await websocket.send_json({"type": "completed", "message": "Interview completed"})
                continue

            if event_type == "user_audio":
                audio_base64 = payload.get("audio_base64")
                if not audio_base64:
                    await websocket.send_json({"type": "error", "message": "audio_base64 is required"})
                    continue

                try:
                    audio_bytes = base64.b64decode(audio_base64)
                except Exception:
                    await websocket.send_json({"type": "error", "message": "Invalid base64 audio"})
                    continue

                filename = payload.get("filename") or "voice_input.webm"
                user_text = openai_service.transcribe_audio(filename=filename, file_bytes=audio_bytes)
            elif event_type == "user_text":
                user_text = str(payload.get("text") or "").strip()
                if not user_text:
                    await websocket.send_json({"type": "error", "message": "text is required for user_text"})
                    continue
            else:
                await websocket.send_json(
                    {"type": "error", "message": "Unsupported type. Use user_audio, user_text, or ping"}
                )
                continue

            transcript_repo.add(
                session_type="interview",
                session_id=interview_session.id,
                speaker="user",
                message=user_text,
                user_id=user_id,
            )

            current_question = questions[current_index]
            next_index = current_index + 1
            next_question = questions[next_index] if next_index < len(questions) else None

            assistant_text = openai_service.build_interview_turn_reply(
                user_answer=user_text,
                current_question=current_question,
                next_question=next_question,
            )

            if next_question is None:
                interview_session.current_index = len(questions)
                interview_session.status = "completed"
                status = "completed"
                question_index = None
                interview_cache.clear_session(interview_session.id)
            else:
                interview_session.current_index = next_index
                status = "active"
                question_index = next_index

            session_repo.save(interview_session)

            transcript_repo.add(
                session_type="interview",
                session_id=interview_session.id,
                speaker="assistant",
                message=assistant_text,
                user_id=user_id,
            )

            assistant_audio, assistant_content_type = openai_service.synthesize_speech(assistant_text)

            await websocket.send_json(
                {
                    "type": "assistant_turn",
                    "user_id": user_id,
                    "interview_session_id": interview_session.id,
                    "status": status,
                    "question_index": question_index,
                    "user_text": user_text,
                    "assistant_text": assistant_text,
                    "assistant_audio_base64": base64.b64encode(assistant_audio).decode("utf-8"),
                    "assistant_audio_content_type": assistant_content_type,
                }
            )

    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1011)
    finally:
        db.close()
