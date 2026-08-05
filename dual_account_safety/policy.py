from __future__ import annotations


READ_OPERATIONS = {
    "ACCOUNT_READ",
    "POSITIONS_READ",
    "ORDERS_READ",
    "BALANCE_READ",
    "PORTFOLIO_READ",
    "HEALTH_READ",
}

WRITE_OPERATIONS = {
    "ORDER_SUBMIT",
    "ORDER_CANCEL",
    "ORDER_REPLACE",
}

PAPER_ONLY_STRATEGY_OPERATIONS = {
    "ORDER_SUBMIT",
    "ORDER_CANCEL",
    "ORDER_REPLACE",
}


def operation_class(operation: str) -> str:
    value = str(operation or "").upper()
    if value in READ_OPERATIONS:
        return "READ"
    if value in WRITE_OPERATIONS:
        return "WRITE"
    return "UNKNOWN"
