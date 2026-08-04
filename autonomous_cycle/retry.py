from __future__ import annotations
from typing import Any

def can_retry(
    attempt_count: int,
    policy: dict[str, Any],
) -> dict[str, Any]:
    maximum_attempts = int(policy.get("maximum_step_attempts", 3))
    retry_allowed = attempt_count < maximum_attempts
    return {
        "attempt_count": attempt_count,
        "maximum_attempts": maximum_attempts,
        "retry_allowed": retry_allowed,
        "remaining_attempts": max(0, maximum_attempts - attempt_count),
    }
