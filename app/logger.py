import asyncio
import json
import re
from datetime import datetime, timezone

from app.config import settings

_lock = asyncio.Lock()

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def mask_pii(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = CARD_RE.sub("[CARD_MASKED]", text)
    text = PHONE_RE.sub("[PHONE_MASKED]", text)
    return text


def mask_entry(entry: dict) -> dict:
    masked = {}
    for k, v in entry.items():
        if isinstance(v, str):
            masked[k] = mask_pii(v)
        else:
            masked[k] = v
    return masked


async def log_exchange(**entry: object) -> None:
    settings.safe_log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **mask_entry(entry)}
    async with _lock:
        with settings.safe_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

