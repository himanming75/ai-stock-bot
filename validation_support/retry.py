from __future__ import annotations
from typing import Any


class RetryPolicy:
    def plan(
        self,
        *,
        category: str,
        attempt: int,
        maximum_attempts: int = 3,
        base_delay_seconds: int = 2,
    ) -> dict[str, Any]:
        retryable = category in {
            "RATE_LIMIT", "BROKER_SERVER", "TIMEOUT", "NETWORK_DNS"
        }
        remaining = attempt < maximum_attempts
        allowed = retryable and remaining
        delay = (
            base_delay_seconds * (2 ** max(0, attempt - 1))
            if allowed else 0
        )
        return {
            "category": category,
            "attempt": attempt,
            "maximum_attempts": maximum_attempts,
            "retry_allowed": allowed,
            "planned_delay_seconds": delay,
            "automatic_retry_enabled": False,
            "automatic_retry_performed": False,
            "operator_approval_required": allowed,
        }


class RateLimitDetector:
    def detect(
        self,
        *,
        status_code: int | None,
        headers: dict[str, Any],
    ) -> dict[str, Any]:
        remaining_raw = headers.get("x-ratelimit-remaining")
        try:
            remaining = (
                int(remaining_raw) if remaining_raw is not None else None
            )
        except Exception:
            remaining = None

        limited = status_code == 429 or remaining == 0
        return {
            "rate_limited": limited,
            "remaining": remaining,
            "reset_at": headers.get("x-ratelimit-reset"),
            "request_block_recommended": limited,
            "automatic_wait_performed": False,
        }
