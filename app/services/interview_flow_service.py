from dataclasses import dataclass
import re

from app.schemas.interview import InterviewSetupPayload


COLLECT_FIELDS = ["readiness", "role", "interview_type", "level", "techstack", "amount"]
FIELD_PROMPTS = {
    "readiness": "Are you ready to begin?",
    "role": "Could you tell me what role you want to train for?",
    "interview_type": "Great. What interview style do you want: technical, behavioral, or mixed?",
    "level": "What level should I target: intern, junior, mid, or senior?",
    "techstack": "Which technologies should we focus on? You can list them separated by commas.",
    "amount": "How many practice questions would you like me to prepare?",
}
FIELD_EXAMPLES = {
    "role": "Examples include frontend developer, backend developer, full stack developer, mobile developer, designer, or data analyst.",
    "interview_type": "For example: technical for coding depth, behavioral for communication, or mixed for both.",
    "level": "Common levels are intern, junior, mid, and senior.",
    "techstack": "For example: React, Next.js, TypeScript or Python, Django, PostgreSQL.",
    "amount": "A good range is usually 5 to 12 questions for one focused practice session.",
}

YES_WORDS = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "ready",
    "lets go",
    "let's go",
    "ok",
    "okay",
    "absolutely",
    "of course",
    "start",
    "go ahead",
}

NOT_READY_WORDS = {
    "no",
    "not yet",
    "later",
    "wait",
    "hold on",
    "one sec",
    "one second",
    "give me a moment",
}

REPEAT_KEYWORDS = {
    "repeat",
    "say again",
    "come again",
    "can you repeat",
    "repeat that",
    "again please",
}

EXAMPLE_KEYWORDS = {
    "example",
    "examples",
    "like what",
    "what roles",
    "can you provide",
    "for instance",
}

CLARIFY_KEYWORDS = {
    "what do you mean",
    "clarify",
    "explain",
    "not sure",
    "i dont understand",
    "i don't understand",
    "confused",
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "twenty one": 21,
    "twenty-two": 22,
    "twenty two": 22,
    "twenty-three": 23,
    "twenty three": 23,
    "twenty-four": 24,
    "twenty four": 24,
    "twenty-five": 25,
    "twenty five": 25,
    "twenty-six": 26,
    "twenty six": 26,
    "twenty-seven": 27,
    "twenty seven": 27,
    "twenty-eight": 28,
    "twenty eight": 28,
    "twenty-nine": 29,
    "twenty nine": 29,
    "thirty": 30,
}


@dataclass
class CollectorProgress:
    next_field: str | None
    completed: bool


class InterviewFlowService:
    @staticmethod
    def build_opening_prompt(candidate_name: str | None = None) -> str:
        if candidate_name:
            return (
                f"Hello {candidate_name}, I’ll ask you a few quick questions so I can prepare the perfect interview for your practice. "
                f"Are you ready to begin?"
            )
        return (
            "Hello, I’ll ask you a few quick questions so I can prepare the perfect interview for your practice. "
            "Are you ready to begin?"
        )

    @staticmethod
    def detect_turn_intent(field_name: str, user_message: str) -> str:
        text = " ".join(user_message.lower().strip().split())
        if not text:
            return "clarify"

        if any(keyword in text for keyword in REPEAT_KEYWORDS):
            return "repeat"
        if any(keyword in text for keyword in EXAMPLE_KEYWORDS):
            return "examples"
        if any(keyword in text for keyword in CLARIFY_KEYWORDS):
            return "clarify"

        if field_name == "readiness":
            if any(word in text for word in NOT_READY_WORDS):
                return "not_ready"
            if any(word in text for word in YES_WORDS):
                return "confirm_ready"
            return "clarify_readiness"

        return "answer"

    @staticmethod
    def build_intent_reply(field_name: str, intent: str) -> str:
        if intent == "repeat":
            return f"Absolutely. {FIELD_PROMPTS[field_name]}"
        if intent == "examples":
            examples = FIELD_EXAMPLES.get(field_name)
            if examples:
                return f"Sure thing. {examples} {FIELD_PROMPTS[field_name]}"
            return f"Sure thing. {FIELD_PROMPTS[field_name]}"
        if intent == "clarify" or intent == "clarify_readiness":
            if field_name == "readiness":
                return "No problem. If you’re ready, just say yes and we’ll start."
            examples = FIELD_EXAMPLES.get(field_name)
            if examples:
                return f"Happy to clarify. {examples} {FIELD_PROMPTS[field_name]}"
            return f"Happy to clarify. {FIELD_PROMPTS[field_name]}"
        if intent == "not_ready":
            return "No worries at all. Take your time, and tell me when you’re ready to start."
        return FIELD_PROMPTS[field_name]

    @staticmethod
    def parse_amount(value: str) -> int:
        digits = re.findall(r"\d+", value)
        if digits:
            return int(digits[0])

        normalized = value.strip().lower().replace("-", " ")
        normalized = " ".join(normalized.split())
        if normalized in NUMBER_WORDS:
            return NUMBER_WORDS[normalized]

        raise ValueError("Please provide a number between 1 and 30.")

    @staticmethod
    def normalize_field_value(field_name: str, user_message: str):
        value = user_message.strip()
        if field_name == "readiness":
            return value
        if field_name == "techstack":
            if "," in value:
                return [item.strip() for item in value.split(",") if item.strip()]
            return [value] if value else []
        if field_name == "amount":
            amount = InterviewFlowService.parse_amount(value)
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
