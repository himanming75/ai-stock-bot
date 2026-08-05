from __future__ import annotations
from decimal import Decimal


def D(value) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def unified_account_summary(
    records: list[dict],
) -> dict:
    total_equity = sum(
        (D(item.get("equity")) for item in records),
        Decimal("0"),
    )
    total_cash = sum(
        (D(item.get("cash")) for item in records),
        Decimal("0"),
    )
    total_buying_power = sum(
        (D(item.get("buying_power")) for item in records),
        Decimal("0"),
    )

    return {
        "account_count": len(records),
        "total_equity": str(total_equity),
        "total_cash": str(total_cash),
        "total_buying_power": str(total_buying_power),
        "currency": "USD",
        "records": records,
    }
