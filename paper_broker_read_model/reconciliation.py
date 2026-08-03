from __future__ import annotations
from typing import Any

def compare_value(
    broker_value: float,
    internal_value: float,
    tolerance: float,
) -> dict[str, Any]:
    difference = broker_value - internal_value
    return {
        "broker_value": round(broker_value, 6),
        "internal_value": round(internal_value, 6),
        "difference": round(difference, 6),
        "tolerance": tolerance,
        "passed": abs(difference) <= tolerance,
    }

def reconcile_account(
    broker: dict[str, Any],
    internal: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    cash = compare_value(
        float(broker.get("cash", 0.0)),
        float(internal.get("cash", 0.0)),
        float(policy.get("cash_tolerance", 0.01)),
    )
    equity = compare_value(
        float(broker.get("equity", 0.0)),
        float(internal.get("equity", 0.0)),
        float(policy.get("equity_tolerance", 0.01)),
    )
    buying_power = compare_value(
        float(broker.get("buying_power", 0.0)),
        float(internal.get("buying_power", 0.0)),
        float(policy.get("buying_power_tolerance", 0.01)),
    )
    checks = {
        "cash": cash["passed"],
        "equity": equity["passed"],
        "buying_power": buying_power["passed"],
        "currency": broker.get("currency") == internal.get("currency"),
        "status": broker.get("status") == internal.get("status"),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "cash": cash,
        "equity": equity,
        "buying_power": buying_power,
        "checks": checks,
        "failed": failed,
    }

def reconcile_positions(
    broker: dict[str, dict[str, Any]],
    internal: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    symbols = sorted(set(broker) | set(internal))
    details = {}
    passed = True
    quantity_tolerance = float(policy.get("quantity_tolerance", 0.000001))
    average_cost_tolerance = float(policy.get("average_cost_tolerance", 0.01))
    market_value_tolerance = float(policy.get("market_value_tolerance", 0.01))

    for symbol in symbols:
        broker_row = broker.get(symbol, {})
        internal_row = internal.get(symbol, {})
        quantity = compare_value(
            float(broker_row.get("quantity", 0.0)),
            float(internal_row.get("quantity", 0.0)),
            quantity_tolerance,
        )
        average_cost = compare_value(
            float(broker_row.get("average_cost", 0.0)),
            float(internal_row.get("average_cost", 0.0)),
            average_cost_tolerance,
        )
        market_value = compare_value(
            float(broker_row.get("market_value", 0.0)),
            float(internal_row.get("market_value", 0.0)),
            market_value_tolerance,
        )
        symbol_passed = (
            quantity["passed"]
            and average_cost["passed"]
            and market_value["passed"]
        )
        passed = passed and symbol_passed
        details[symbol] = {
            "passed": symbol_passed,
            "quantity": quantity,
            "average_cost": average_cost,
            "market_value": market_value,
            "broker_present": symbol in broker,
            "internal_present": symbol in internal,
        }

    return {
        "passed": passed,
        "symbol_count": len(symbols),
        "details": details,
    }
