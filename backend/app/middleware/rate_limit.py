"""
Rate Limiting Middleware
"""
import time
from typing import Dict, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, status
from ..config import settings


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)

    def _cleanup_old_requests(self, key: str, window: int):
        """Remove requests outside the time window."""
        current_time = time.time()
        self.requests[key] = [
            ts for ts in self.requests[key]
            if current_time - ts < window
        ]

    def is_allowed(
        self,
        key: str,
        max_requests: Optional[int] = None,
        window: Optional[int] = None,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        Returns (is_allowed, remaining, reset_in_seconds).
        """
        if not settings.rate_limit_enabled:
            return True, 999, 0

        max_requests = max_requests or settings.rate_limit_requests
        window = window or settings.rate_limit_window

        self._cleanup_old_requests(key, window)

        current_count = len(self.requests[key])
        remaining = max(0, max_requests - current_count - 1)

        if current_count >= max_requests:
            # Find when the oldest request will expire
            oldest = min(self.requests[key]) if self.requests[key] else time.time()
            reset_in = int(window - (time.time() - oldest))
            return False, 0, reset_in

        self.requests[key].append(time.time())
        return True, remaining, window


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request,
    key: str,
    max_requests: Optional[int] = None,
    window: Optional[int] = None,
):
    """Check rate limit and raise exception if exceeded."""
    is_allowed, remaining, reset_in = rate_limiter.is_allowed(
        key, max_requests, window
    )

    # Add rate limit headers
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = reset_in

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_in),
                "Retry-After": str(reset_in),
            },
        )
