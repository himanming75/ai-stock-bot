from __future__ import annotations


OPEN_STATUSES = {
    "OPEN",
    "PENDING",
    "PLACED",
    "QUEUED",
    "PARTIALLY_FILLED",
    "PARTIAL",
}

FILLED_STATUSES = {
    "FILLED",
    "EXECUTED",
}

CANCELLED_STATUSES = {
    "CANCELLED",
    "CANCELED",
}

REJECTED_STATUSES = {
    "REJECTED",
    "EXPIRED",
}


def canonical_order_status(status: str) -> str:
    value = str(status or "UNKNOWN").upper()
    if value in OPEN_STATUSES:
        return "OPEN"
    if value in FILLED_STATUSES:
        return "FILLED"
    if value in CANCELLED_STATUSES:
        return "CANCELLED"
    if value in REJECTED_STATUSES:
        return "REJECTED"
    return "UNKNOWN"


def is_open_order(status: str) -> bool:
    return canonical_order_status(status) == "OPEN"
