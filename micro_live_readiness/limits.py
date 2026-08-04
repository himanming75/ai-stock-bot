from __future__ import annotations
from typing import Any

def evaluate_candidate(candidate:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    checks={
        "symbol_allowed":candidate.get("symbol") in set(policy.get("allowed_symbols",[])),
        "quantity_positive":float(candidate.get("quantity",0.0))>0,
        "quantity_within_limit":float(candidate.get("quantity",0.0))<=float(policy.get("maximum_quantity",1)),
        "notional_within_limit":float(candidate.get("estimated_notional",0.0))<=float(policy.get("maximum_order_notional",100.0)),
        "order_type_allowed":candidate.get("order_type") in set(policy.get("allowed_order_types",["limit"])),
        "daily_order_count_within_limit":int(policy.get("current_daily_live_order_count",0))<int(policy.get("maximum_daily_live_orders",1)),
        "daily_loss_clear":float(policy.get("current_daily_live_pnl",0.0))>-abs(float(policy.get("maximum_daily_live_loss",20.0))),
        "paper_qualification_required":policy.get("paper_qualification_required") is True,
        "paper_qualification_passed":policy.get("paper_qualification_passed") is True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"candidate_id":candidate.get("candidate_id"),"passed":not failed,"checks":checks,"failed":failed}

def evaluate_all(candidates,policy):
    rows=[evaluate_candidate(c,policy) for c in candidates]
    return {
        "rows":rows,
        "passed":bool(rows) and all(r["passed"] for r in rows),
        "eligible_count":sum(1 for r in rows if r["passed"]),
        "ineligible_count":sum(1 for r in rows if not r["passed"]),
    }
