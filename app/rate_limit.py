import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings


class RateLimiter:
    def __init__(self, max_keys: int = 10000) -> None:
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()
        self.max_keys = max_keys

    def _cleanup_expired(self, now: float) -> None:
        expired_keys = [
            key for key, bucket in self.requests.items()
            if not bucket or now - bucket[-1] > settings.rate_limit_window_seconds
        ]
        for key in expired_keys:
            del self.requests[key]

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        if settings.trust_proxy:
            forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            key = forwarded or client_ip
        else:
            key = client_ip

        now = time.monotonic()
        async with self.lock:
            if len(self.requests) > 100:
                self._cleanup_expired(now)
            bucket = self.requests[key]
            while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
                bucket.popleft()
            if len(bucket) >= settings.rate_limit_requests:
                raise HTTPException(429, "Слишком много запросов. Попробуйте позже.")
            bucket.append(now)


rate_limiter = RateLimiter()

