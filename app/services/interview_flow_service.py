from dataclasses import dataclass

from app.schemas.interview import InterviewSetupPayload


COLLECT_FIELDS = ["role", "interview_type", "level", "techstack", "amount"]
FIELD_PROMPTS = {
    "role": "What role would you like to train for? For example: Frontend, Backend, Fullstack, Design, UX.",
    "interview_type": "Are you aiming for a technical, behavioral, or mixed interview?",
    "level": "What is the job experience level? For example: Intern, Junior, Mid, Senior.",
    "techstack": "Please share the technologies to cover, separated by commas. For example: Next.js, React, Python, Java.",
    "amount": "How many questions would you like me to prepare for you?",
}


@dataclass
class CollectorProgress:
    next_field: str | None
    completed: bool


class InterviewFlowService:
    @staticmethod
    def normalize_field_value(field_name: str, user_message: str):
        value = user_message.strip()
        if field_name == "techstack":
            return [item.strip() for item in value.split(",") if item.strip()]
        if field_name == "amount":
            amount = int(value)
            if amount < 1 or amount > 30:
                raise ValueError("Amount must be between 1 and 30.")
            return amount
        return value

    @staticmethod
    def get_next_field(current_field: str) -> CollectorProgress:
        idx = COLLECT_FIELDS.index(current_field)
        if idx == len(COLLECT_FIELDS) - 1:
            return CollectorProgress(next_field=None, completed=True)
        return CollectorProgress(next_field=COLLECT_FIELDS[idx + 1], completed=False)

    @staticmethod
    def build_payload(raw_payload: dict) -> InterviewSetupPayload:
        return InterviewSetupPayload(
            role=raw_payload["role"],
            interview_type=raw_payload["interview_type"],
            level=raw_payload["level"],
            techstack=raw_payload["techstack"],
            amount=raw_payload["amount"],
        )
