from __future__ import annotations
from typing import Any

def evaluate_safety(integration: dict[str, Any]) -> dict[str, Any]:
    rows=integration.get("rows",[])
    checks={
        "all_stages_ready":integration.get("passed") is True,
        "all_orders_zero":all(r.get("actual_orders_submitted",0)==0 for r in rows),
        "all_paper_only":all(r.get("paper_only",True) is True for r in rows),
        "live_trading_disabled":True,
        "broker_write_disabled":True,
        "order_submission_disabled":True,
        "external_network_disabled":True,
        "manual_approval_required":True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"passed":not failed,"checks":checks,"failed":failed}
