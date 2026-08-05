from __future__ import annotations


def calculate_backoff(
    attempt_number: int,
    *,
    base_seconds: int,
    maximum_seconds: int,
) -> int:
    attempt = max(1, int(attempt_number))
    value = base_seconds * (2 ** (attempt - 1))
    return min(value, maximum_seconds)
