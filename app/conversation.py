import asyncio
import re
import time
from dataclasses import dataclass


FOLLOW_UP_RE = re.compile(
    r"^(?:а|и|но|тогда|ещ[её]|также)\b|^(?:для|на|про)\s+|"
    r"^(?:что насч[её]т|а что насч[её]т|как тогда|почему так|как это)\b",
    re.I,
)


@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str


def expand_follow_up(message: str, previous_user: str | None) -> str:
    text = " ".join(message.split())
    if not previous_user or len(text.split()) > 12 or not FOLLOW_UP_RE.search(text):
        return text
    return f"Предыдущий вопрос: {previous_user}\nУточнение пользователя: {text}"


class ConversationStore:
    def __init__(self, ttl_seconds: int = 3600, max_turns: int = 6) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self._sessions: dict[str, tuple[float, list[Turn]]] = {}
        self._lock = asyncio.Lock()

    async def last_user(self, session_id: str) -> str | None:
        async with self._lock:
            record = self._sessions.get(session_id)
            if not record:
                return None
            updated_at, turns = record
            if time.monotonic() - updated_at > self.ttl_seconds:
                self._sessions.pop(session_id, None)
                return None
            return turns[-1].user if turns else None

    async def add(self, session_id: str, user: str, assistant: str) -> None:
        async with self._lock:
            turns = list(self._sessions.get(session_id, (0.0, []))[1])
            turns.append(Turn(user=user, assistant=assistant))
            self._sessions[session_id] = (time.monotonic(), turns[-self.max_turns:])
