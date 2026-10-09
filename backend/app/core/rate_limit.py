"""
In-memory rate limiting middleware and dependencies
"""

import time
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.records: Dict[str, list[float]] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0

        if client_ip not in self.records:
            self.records[client_ip] = [now]
            return True, self.requests_per_minute - 1

        # Clean old timestamps
        timestamps = [ts for ts in self.records[client_ip] if ts > window_start]
        self.records[client_ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            return False, 0

        self.records[client_ip].append(now)
        return True, self.requests_per_minute - len(self.records[client_ip])


login_limiter = InMemoryRateLimiter(requests_per_minute=5)
upload_limiter = InMemoryRateLimiter(requests_per_minute=10)
scoring_limiter = InMemoryRateLimiter(requests_per_minute=5)
default_limiter = InMemoryRateLimiter(requests_per_minute=120)


def reset_all_limiters():
    """Resets all in-memory rate limiters (used on demo reset and between tests)."""
    login_limiter.records.clear()
    upload_limiter.records.clear()
    scoring_limiter.records.clear()
    default_limiter.records.clear()


def rate_limit_check(limiter: InMemoryRateLimiter):
    def dependency(request: Request):
        from app.core.config import settings
        if settings.ENVIRONMENT != "production" and request.headers.get("x-e2e-test") == "1":
            return
        client_ip = request.client.host if request.client else "127.0.0.1"
        allowed, remaining = limiter.is_allowed(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please retry later."}}
            )
    return dependency
