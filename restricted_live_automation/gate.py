from __future__ import annotations
from datetime import datetime
from typing import Any

def _time_ok(now_hm:str,start:str,cutoff:str)->bool:
    return start<=now_hm<=cutoff

def evaluate(policy:dict[str,Any],qualification:dict[str,Any],micro:dict[str,Any],candidate:dict[str,Any])->dict[str,Any]:
    now_hm=datetime.now().strftime("%H:%M")
    symbol=str(candidate.get("symbol",""))
    strategy=str(candidate.get("strategy_id",""))
    qty=float(candidate.get("quantity",candidate.get("qty",0)) or 0)
    notional=float(candidate.get("estimated_notional",0) or 0)
    checks={
      "qualification_passed":qualification.get("qualification",{}).get("passed") is True,
      "micro_live_dry_run_ready":micro.get("dry_run_ready") is True,
      "micro_execution_not_authorized":micro.get("execution_authorized") is False,
      "candidate_present":bool(candidate),
      "symbol_allowed":symbol in policy.get("allowed_symbols",[]),
      "strategy_allowed":strategy in policy.get("allowed_strategies",[]),
      "trading_time_allowed":_time_ok(now_hm,policy["trading_start"],policy["new_order_cutoff"]),
      "quantity_exactly_one":qty==1,
      "notional_within_limit":0<notional<=policy["maximum_order_notional"],
      "automatic_submission_disabled":policy.get("automatic_submission_enabled") is False,
      "live_network_disabled":policy.get("live_network_enabled") is False,
      "live_write_disabled":policy.get("live_write_enabled") is False,
      "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"passed":not failed,"checks":checks,"failed":failed,"evaluated_time":now_hm}
