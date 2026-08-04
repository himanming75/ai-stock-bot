from __future__ import annotations
from typing import Any
from micro_live_readiness.io import digest

def build_candidates(source:dict[str,Any],policy:dict[str,Any])->list[dict[str,Any]]:
    rows=[]
    for plan in source.get("paper_order_plans",[]):
        notional=float(plan.get("estimated_notional",0.0))
        body={
            "candidate_id":digest(plan)[:24],
            "symbol":plan.get("symbol"),
            "side":plan.get("side"),
            "quantity":float(plan.get("qty",0.0)),
            "order_type":plan.get("type"),
            "time_in_force":plan.get("time_in_force"),
            "estimated_notional":notional,
            "source_client_order_id":plan.get("client_order_id"),
            "source_strategy_id":plan.get("strategy_id"),
            "live_order_submitted":False,
        }
        rows.append(body)
    return rows
