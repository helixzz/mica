"""Simple in-memory rate limiter for auth endpoints."""

import time
from collections import defaultdict

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < 300:  # clean every 5 min
            return
        cutoff = now - self.window_seconds
        for ip in list(self._attempts.keys()):
            self._attempts[ip] = [t for t in self._attempts[ip] if t > cutoff]
            if not self._attempts[ip]:
                del self._attempts[ip]
        self._last_cleanup = now

    def check(self, ip: str) -> None:
        self._cleanup()
        now = time.time()
        cutoff = now - self.window_seconds
        self._attempts[ip] = [t for t in self._attempts[ip] if t > cutoff]
        if len(self._attempts[ip]) >= self.max_attempts:
            retry_after = int(self._attempts[ip][0] + self.window_seconds - now)
            raise HTTPException(
                429,
                detail="auth.rate_limited",
                headers={"Retry-After": str(retry_after)},
            )
        self._attempts[ip].append(now)

    def reset(self, ip: str) -> None:
        self._attempts.pop(ip, None)


auth_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60)
