from __future__ import annotations
from typing import Any

def execute_with_retry(fn, attempts: int) -> dict[str, Any]:
    errors=[]
    for attempt in range(1,max(1,attempts)+1):
        try:
            result=fn()
            return {
                "passed":True,
                "attempt_count":attempt,
                "errors":errors,
                "result":result,
            }
        except Exception as exc:
            errors.append(str(exc))
    return {
        "passed":False,
        "attempt_count":max(1,attempts),
        "errors":errors,
        "result":None,
    }
