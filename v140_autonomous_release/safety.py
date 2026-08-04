from __future__ import annotations
from typing import Any

def evaluate(sources:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    live_orders=sum(int(v.get("actual_live_orders_submitted",0)) for v in sources.values())
    checks={
        "all_sources_present":all(bool(v) for v in sources.values()),
        "all_status_pass":all(v.get("status")=="PASS" for v in sources.values()),
        "historical_live_orders_zero":live_orders==0,
        "live_network_disabled":policy.get("live_network_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
        "manual_live_enable_required":policy.get("manual_live_enable_required") is True,
        "paper_mode_default":policy.get("default_mode")=="PAPER",
        "kill_switch_default_enabled":policy.get("kill_switch_default_enabled") is True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "historical_live_orders_submitted":live_orders,
        "actual_live_orders_submitted":0,
    }
