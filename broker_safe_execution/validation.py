from __future__ import annotations
from typing import Any

def validate_intent(
    intent: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    allowed_symbols=set(policy.get("allowed_symbols",[]))
    allowed_sides={"BUY","SELL"}
    allowed_types={"MARKET","LIMIT","STOP","STOP_LIMIT"}
    checks={
        "symbol_allowed":intent.get("symbol") in allowed_symbols,
        "side_allowed":intent.get("side") in allowed_sides,
        "order_type_allowed":intent.get("order_type") in allowed_types,
        "quantity_positive":float(intent.get("quantity",0.0))>0,
        "quantity_within_limit":float(intent.get("quantity",0.0))
            <=float(policy.get("maximum_order_quantity",1000)),
        "notional_within_limit":float(intent.get("estimated_notional",0.0))
            <=float(policy.get("maximum_order_notional",25000.0)),
        "limit_price_present_when_required":(
            intent.get("order_type") not in {"LIMIT","STOP_LIMIT"}
            or intent.get("limit_price") is not None
        ),
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "intent_id":intent.get("intent_id"),
        "passed":not failed,
        "checks":checks,
        "failed":failed,
    }

def validate_all(
    intents: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    rows=[validate_intent(row,policy) for row in intents]
    return {
        "rows":rows,
        "passed":all(row["passed"] for row in rows),
        "valid_count":sum(1 for row in rows if row["passed"]),
        "invalid_count":sum(1 for row in rows if not row["passed"]),
    }
