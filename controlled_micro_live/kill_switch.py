from __future__ import annotations
from typing import Any

def evaluate(policy:dict[str,Any],candidate:dict[str,Any])->dict[str,Any]:
    checks={
        "manual_kill_switch_clear":policy.get("manual_kill_switch") is False,
        "daily_loss_clear":float(policy.get("current_daily_pnl",0.0))>-abs(float(policy.get("maximum_daily_loss",20.0))),
        "daily_order_limit_clear":int(policy.get("current_daily_order_count",0))<int(policy.get("maximum_daily_orders",1)),
        "candidate_notional_clear":float(candidate.get("estimated_notional",0.0))<=float(policy.get("maximum_notional",250.0)),
        "candidate_quantity_clear":float(candidate.get("quantity",0.0))<=float(policy.get("maximum_quantity",1.0)),
        "market_required":policy.get("market_open_required") is True,
        "market_open":policy.get("market_open") is True,
        "broker_healthy":policy.get("broker_health")=="HEALTHY",
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "state":"KILL_SWITCH_CLEAR" if not failed else "KILL_SWITCH_BLOCKED",
    }
