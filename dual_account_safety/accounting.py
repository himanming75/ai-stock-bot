from __future__ import annotations
from decimal import Decimal


def D(value) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def segregated_account_summary(
    account_snapshots: list[dict],
) -> dict:
    paper = []
    actual = []

    for item in account_snapshots:
        environment = str(
            item.get("environment") or ""
        ).upper()
        if environment == "PAPER":
            paper.append(item)
        else:
            actual.append(item)

    def totals(items: list[dict]) -> dict:
        return {
            "account_count": len(items),
            "equity": str(sum(
                (D(item.get("equity")) for item in items),
                Decimal("0"),
            )),
            "cash": str(sum(
                (D(item.get("cash")) for item in items),
                Decimal("0"),
            )),
            "unrealized_pl": str(sum(
                (
                    D(item.get("unrealized_pl"))
                    for item in items
                ),
                Decimal("0"),
            )),
        }

    return {
        "paper": totals(paper),
        "actual": totals(actual),
        "combined_reference_only": {
            "equity": str(sum(
                (
                    D(item.get("equity"))
                    for item in account_snapshots
                ),
                Decimal("0"),
            )),
            "must_not_be_used_for_strategy_sizing": True,
        },
        "paper_and_actual_performance_mixed": False,
    }
