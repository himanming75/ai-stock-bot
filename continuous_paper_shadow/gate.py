from __future__ import annotations
from typing import Any

def evaluate_plan(plan:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    checks={
        "symbol_allowed":plan.get("symbol") in set(policy.get("symbols",[])),
        "quantity_positive":float(plan.get("qty",0))>0,
        "quantity_within_limit":float(plan.get("qty",0))<=float(policy.get("maximum_quantity",2)),
        "notional_within_limit":float(plan.get("estimated_notional",0))<=float(policy.get("maximum_order_notional",250)),
        "paper_mode":policy.get("paper_mode") is True,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"passed":not failed,"checks":checks,"failed":failed}

def evaluate_all(plans,policy):
    rows=[{"client_order_id":p.get("client_order_id"),**evaluate_plan(p,policy)} for p in plans]
    return {"rows":rows,"passed":all(r["passed"] for r in rows),"valid_count":sum(r["passed"] for r in rows)}
