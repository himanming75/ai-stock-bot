from __future__ import annotations

RETRYABLE_REASONS = {
    "RATE_LIMITED",
    "BROKER_SERVER_ERROR",
    "NETWORK_OR_TIMEOUT",
}

TERMINAL_REASONS = {
    "REJECTED",
    "ACCEPTED",
    "UNKNOWN_RESPONSE",
}


def classify_reason(reason: str) -> dict:
    if reason in RETRYABLE_REASONS:
        return {
            "classification": "RETRYABLE",
            "retryable": True,
            "terminal": False,
        }
    if reason in TERMINAL_REASONS:
        return {
            "classification": "TERMINAL",
            "retryable": False,
            "terminal": True,
        }
    return {
        "classification": "MANUAL_REVIEW",
        "retryable": False,
        "terminal": False,
    }
