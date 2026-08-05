from __future__ import annotations


def severity_for(event_type: str, delta=None) -> str:
    critical = {
        "POSITION_CLOSED_UNEXPECTED",
        "ACCOUNT_STATUS_CHANGED_TO_RESTRICTED",
        "DUPLICATE_ORDER_ID",
        "SNAPSHOT_INTEGRITY_FAILED",
    }
    warnings = {
        "POSITION_OPENED",
        "POSITION_CLOSED",
        "POSITION_QUANTITY_CHANGED",
        "POSITION_AVERAGE_PRICE_CHANGED",
        "ORDER_STATUS_CHANGED",
        "ACCOUNT_EQUITY_CHANGED",
        "ACCOUNT_CASH_CHANGED",
        "ACCOUNT_BUYING_POWER_CHANGED",
    }

    if event_type in critical:
        return "CRITICAL"
    if event_type in warnings:
        return "WARNING"
    return "INFO"
