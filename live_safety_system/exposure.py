from __future__ import annotations
from typing import Any

def evaluate_exposure(
    policy: dict[str, Any],
    execution: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    equity=float(telemetry.get("account_equity",0.0))
    intents=execution.get("order_intents",[])
    order_notionals=[float(row.get("estimated_notional",0.0)) for row in intents]
    largest=max(order_notionals) if order_notionals else 0.0
    total=sum(order_notionals)
    position_count=int(telemetry.get("open_position_count",0))
    gross=float(telemetry.get("gross_exposure",0.0))
    checks={
        "largest_order_within_limit":largest<=float(
            policy.get("maximum_single_order_notional",5000.0)
        ),
        "total_pending_orders_within_limit":total<=float(
            policy.get("maximum_pending_order_notional",10000.0)
        ),
        "position_count_within_limit":position_count<=int(
            policy.get("maximum_open_positions",10)
        ),
        "gross_exposure_within_limit":gross<=equity*float(
            policy.get("maximum_gross_exposure_pct",100.0)
        )/100.0,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "largest_order_notional":round(largest,2),
        "total_pending_order_notional":round(total,2),
        "open_position_count":position_count,
        "gross_exposure":round(gross,2),
        "checks":checks,
        "failed":failed,
        "passed":not failed,
    }
