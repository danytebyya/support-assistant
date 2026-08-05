import asyncio
import re
import time
from dataclasses import dataclass


FOLLOW_UP_RE = re.compile(
    r"^(?:тогда|ещ[её]|также)\b|^(?:а\s+|и\s+|но\s+)?(?:для|на|про)\s+|"
    r"^(?:а что|а как|а где|а можно|что насч[её]т|а что насч[её]т|как тогда|почему так|как это)\b",
    re.I,
)


@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str
    context: str


def extract_clean_context(text: str) -> str:
    lines = text.split("\n")
    parts = []
    for line in lines:
        cleaned = re.sub(r"^(?:Предыдущий вопрос|Уточнение пользователя|Вопрос пользователя|Уточнение):\s*", "", line, flags=re.I).strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return " ".join(parts)


def expand_follow_up(message: str, previous_user: str | None) -> str:
    text = " ".join(message.split())
    if not previous_user or len(text.split()) > 12 or not FOLLOW_UP_RE.search(text):
        return text
    clean_prev = extract_clean_context(previous_user)
    return f"Предыдущий вопрос: {clean_prev}\nУточнение пользователя: {text}"


class ConversationStore:
    def __init__(self, ttl_seconds: int = 3600, max_turns: int = 6, max_sessions: int = 5000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self.max_sessions = max_sessions
        self._sessions: dict[str, tuple[float, list[Turn]]] = {}
        self._lock = asyncio.Lock()

    def _cleanup_expired_locked(self, now: float) -> None:
        expired = [
            sid for sid, (updated_at, _) in self._sessions.items()
            if now - updated_at > self.ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]

    async def last_user(self, session_id: str) -> str | None:
        async with self._lock:
            now = time.monotonic()
            self._cleanup_expired_locked(now)
            record = self._sessions.get(session_id)
            if not record:
                return None
            _, turns = record
            return turns[-1].context if turns else None

    async def add(self, session_id: str, user: str, assistant: str, context: str | None = None) -> None:
        async with self._lock:
            now = time.monotonic()
            if len(self._sessions) >= self.max_sessions:
                self._cleanup_expired_locked(now)
                if len(self._sessions) >= self.max_sessions:
                    oldest_sid = min(self._sessions.keys(), key=lambda k: self._sessions[k][0])
                    del self._sessions[oldest_sid]
            turns = list(self._sessions.get(session_id, (0.0, []))[1])
            turns.append(Turn(user=user, assistant=assistant, context=context or user))
            self._sessions[session_id] = (now, turns[-self.max_turns:])
