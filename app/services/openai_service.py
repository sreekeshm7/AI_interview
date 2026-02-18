import json
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.schemas.interview import InterviewSetupPayload


class OpenAIService:
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Set it in deployment environment variables.")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_interview_questions(self, payload: InterviewSetupPayload) -> List[str]:
        prompt = (
            "You are an expert technical interviewer. "
            "Generate interview questions for a candidate with this configuration:\n"
            f"Role: {payload.role}\n"
            f"Interview Type: {payload.interview_type}\n"
            f"Level: {payload.level}\n"
            f"Tech Stack: {', '.join(payload.techstack)}\n"
            f"Amount: {payload.amount}\n\n"
            "Rules:\n"
            "1) Return exactly the requested number of questions.\n"
            "2) Questions should be concise and clear.\n"
            "3) Keep difficulty aligned to level.\n"
            "4) No headings or numbering in the question text itself.\n"
            "Return JSON only in this format: {\"questions\": [\"...\", \"...\"]}."
        )

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.5,
            messages=[
                {"role": "system", "content": "You return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content or "{}"
        cleaned = self._strip_json_fences(raw)
        data = json.loads(cleaned)
        questions = data.get("questions", [])

        if not isinstance(questions, list) or len(questions) != payload.amount:
            raise ValueError("OpenAI returned invalid question payload.")

        normalized = [str(q).strip() for q in questions if str(q).strip()]
        if len(normalized) != payload.amount:
            raise ValueError("OpenAI returned empty or malformed questions.")

        return normalized

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip()
        return stripped

    def build_collector_reply(self, field_name: str, user_response: str, next_field_prompt: str | None) -> str:
        user_prompt = (
            "You are a warm voice interview assistant collecting setup details. "
            "Acknowledge the user's answer naturally in one short sentence. "
            "Then, if a next prompt exists, ask it clearly in one sentence.\n\n"
            f"Current field answered: {field_name}\n"
            f"User response: {user_response}\n"
            f"Next prompt: {next_field_prompt or 'NONE'}"
        )

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": "Speak naturally and briefly, with no bullet points.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )

        return (response.choices[0].message.content or "").strip()

    def build_interview_turn_reply(self, user_answer: str, current_question: str, next_question: str | None) -> str:
        user_prompt = (
            "You are a realistic interview voice AI. "
            "Acknowledge the candidate's answer naturally in one short sentence. "
            "If next_question exists, transition and ask it naturally. "
            "If next_question is NONE, close the interview politely in one sentence.\n\n"
            f"Question just answered: {current_question}\n"
            f"Candidate answer: {user_answer}\n"
            f"Next question: {next_question or 'NONE'}"
        )

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": "Human, concise, professional interviewer style. No bullets.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )

        return (response.choices[0].message.content or "").strip()

    def transcribe_audio(self, filename: str, file_bytes: bytes) -> str:
        from io import BytesIO

        audio_buffer = BytesIO(file_bytes)
        audio_buffer.name = filename

        transcription = self.client.audio.transcriptions.create(
            model=settings.openai_transcribe_model,
            file=audio_buffer,
        )
        return transcription.text.strip()

    def synthesize_speech(self, text: str) -> tuple[bytes, str]:
        speech = self.client.audio.speech.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=text,
            response_format=settings.openai_tts_format,
        )

        audio_bytes = b""
        if hasattr(speech, "read"):
            audio_bytes = speech.read()
        elif hasattr(speech, "content"):
            audio_bytes = speech.content

        if not audio_bytes:
            raise ValueError("OpenAI TTS returned empty audio")

        content_type = f"audio/{settings.openai_tts_format}"
        return audio_bytes, content_type
