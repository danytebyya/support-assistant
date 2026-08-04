import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def __call__(self, request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        key = forwarded or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        async with self.lock:
            bucket = self.requests[key]
            while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
                bucket.popleft()
            if len(bucket) >= settings.rate_limit_requests:
                raise HTTPException(429, "Слишком много запросов. Попробуйте позже.")
            bucket.append(now)


rate_limiter = RateLimiter()

