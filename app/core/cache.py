from threading import Lock
from time import time


class InterviewMemoryCache:
    def __init__(self, ttl_seconds: int = 7200):
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._interview_questions: dict[int, tuple[float, list[str]]] = {}
        self._session_questions: dict[int, tuple[float, list[str]]] = {}

    def _get(self, store: dict[int, tuple[float, list[str]]], key: int) -> list[str] | None:
        with self._lock:
            item = store.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at < time():
                del store[key]
                return None
            return value

    def _set(self, store: dict[int, tuple[float, list[str]]], key: int, value: list[str]):
        with self._lock:
            store[key] = (time() + self.ttl_seconds, value)

    def get_interview_questions(self, interview_id: int) -> list[str] | None:
        return self._get(self._interview_questions, interview_id)

    def set_interview_questions(self, interview_id: int, questions: list[str]):
        self._set(self._interview_questions, interview_id, questions)

    def get_session_questions(self, interview_session_id: int) -> list[str] | None:
        return self._get(self._session_questions, interview_session_id)

    def set_session_questions(self, interview_session_id: int, questions: list[str]):
        self._set(self._session_questions, interview_session_id, questions)

    def clear_session(self, interview_session_id: int):
        with self._lock:
            if interview_session_id in self._session_questions:
                del self._session_questions[interview_session_id]


interview_cache = InterviewMemoryCache()
