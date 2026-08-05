from __future__ import annotations


def map_response(status_code: int | None, body: dict | None) -> dict:
    body = body or {}
    if status_code in {200, 201}:
        return {
            "classification": "ACCEPTED",
            "retryable": False,
            "terminal": True,
        }
    if status_code in {400, 401, 403, 404, 422}:
        return {
            "classification": "REJECTED",
            "retryable": False,
            "terminal": True,
        }
    if status_code == 429:
        return {
            "classification": "RATE_LIMITED",
            "retryable": True,
            "terminal": False,
        }
    if status_code is not None and 500 <= status_code <= 599:
        return {
            "classification": "BROKER_SERVER_ERROR",
            "retryable": True,
            "terminal": False,
        }
    if status_code is None:
        return {
            "classification": "NETWORK_OR_TIMEOUT",
            "retryable": True,
            "terminal": False,
        }
    return {
        "classification": "UNKNOWN_RESPONSE",
        "retryable": False,
        "terminal": True,
    }
