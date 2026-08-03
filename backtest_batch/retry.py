from __future__ import annotations
from typing import Any, Callable

def execute_with_retry(
    job: dict[str, Any],
    runner: Callable[[dict[str, Any]], dict[str, Any]],
    maximum_retries: int,
) -> dict[str, Any]:
    attempts=0
    last_error=""
    while attempts <= maximum_retries:
        attempts += 1
        try:
            result=runner(job)
            result["attempt_count"]=attempts
            return result
        except Exception as exc:
            last_error=f"{type(exc).__name__}: {exc}"
    return {
        **job,
        "state":"FAILED_AFTER_RETRIES",
        "status":"FAIL",
        "attempt_count":attempts,
        "error":last_error,
    }
