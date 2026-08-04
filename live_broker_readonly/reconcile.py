from __future__ import annotations
from typing import Any

def compare_number(
    internal: float,
    broker: float,
    tolerance: float,
) -> dict[str, Any]:
    difference=round(float(broker)-float(internal),6)
    return {
        "internal_value":internal,
        "broker_value":broker,
        "difference":difference,
        "tolerance":tolerance,
        "passed":abs(difference)<=tolerance,
    }

def reconcile(
    internal_account: dict[str, Any],
    internal_positions: list[dict[str, Any]],
    broker_account: dict[str, Any],
    broker_positions: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    money_tolerance=float(policy.get("money_tolerance",1.0))
    quantity_tolerance=float(policy.get("quantity_tolerance",0.000001))
    account={
        "cash":compare_number(
            float(internal_account.get("cash",0.0)),
            float(broker_account.get("cash",0.0)),
            money_tolerance,
        ),
        "equity":compare_number(
            float(internal_account.get("equity",0.0)),
            float(broker_account.get("equity",0.0)),
            money_tolerance,
        ),
    }
    internal_lookup={
        str(row.get("symbol")):row for row in internal_positions
    }
    broker_lookup={
        str(row.get("symbol")):row for row in broker_positions
    }
    symbols=sorted(set(internal_lookup)|set(broker_lookup))
    position_details={}
    for symbol in symbols:
        internal=internal_lookup.get(symbol,{})
        broker=broker_lookup.get(symbol,{})
        quantity=compare_number(
            float(internal.get("quantity",0.0)),
            float(broker.get("quantity",0.0)),
            quantity_tolerance,
        )
        market_value=compare_number(
            float(internal.get("market_value",0.0)),
            float(broker.get("market_value",0.0)),
            money_tolerance,
        )
        position_details[symbol]={
            "internal_present":symbol in internal_lookup,
            "broker_present":symbol in broker_lookup,
            "quantity":quantity,
            "market_value":market_value,
            "passed":quantity["passed"] and market_value["passed"],
        }
    account_passed=all(item["passed"] for item in account.values())
    positions_passed=all(
        item["passed"] for item in position_details.values()
    )
    return {
        "account":account,
        "positions":position_details,
        "account_reconciled":account_passed,
        "positions_reconciled":positions_passed,
        "passed":account_passed and positions_passed,
    }
