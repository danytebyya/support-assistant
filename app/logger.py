import asyncio
import json
from datetime import datetime, timezone

from app.config import settings

_lock = asyncio.Lock()


async def log_exchange(**entry: object) -> None:
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **entry}
    async with _lock:
        with settings.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

