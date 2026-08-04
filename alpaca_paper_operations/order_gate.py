from __future__ import annotations
from typing import Any

def validate_order(payload:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    symbols=set(policy.get("allowed_symbols",[]))
    qty=float(payload.get("qty",0))
    checks={
        "symbol_allowed":payload.get("symbol") in symbols,
        "side_allowed":payload.get("side") in {"buy","sell"},
        "type_allowed":payload.get("type") in {"market","limit","stop","stop_limit"},
        "time_in_force_allowed":payload.get("time_in_force") in {"day","gtc","ioc","fok"},
        "quantity_positive":qty>0,
        "quantity_within_limit":qty<=float(policy.get("maximum_quantity",10)),
        "paper_mode":policy.get("paper_mode") is True,
        "live_base_url_prohibited":policy.get("live_base_url_prohibited") is True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"passed":not failed,"checks":checks,"failed":failed}

def submission_gate(
    validation:dict[str,Any],
    policy:dict[str,Any],
    explicit_submit:bool,
    credentials_complete:bool,
)->dict[str,Any]:
    checks={
        "validation_passed":validation.get("passed") is True,
        "explicit_submit_requested":explicit_submit is True,
        "paper_submission_enabled":policy.get("paper_submission_enabled") is True,
        "credentials_complete":credentials_complete is True,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    authorized=all(checks.values())
    return {
        "authorized":authorized,
        "checks":checks,
        "state":"PAPER_SUBMISSION_AUTHORIZED" if authorized else "PAPER_SUBMISSION_BLOCKED",
    }
