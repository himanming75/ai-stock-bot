from __future__ import annotations
from typing import Any

def evaluate(portfolio:dict[str,Any],health:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    summary=portfolio.get("summary",{})
    max_weight=max([float(x.get("weight_pct",0)) for x in portfolio.get("broker_allocation",[])] or [0])
    checks={
        "maximum_brokers":summary.get("broker_count",0)<=int(policy["maximum_brokers"]),
        "maximum_accounts":summary.get("account_count",0)<=int(policy["maximum_accounts"]),
        "maximum_positions":summary.get("position_count",0)<=int(policy["maximum_positions"]),
        "maximum_broker_weight_pct":max_weight<=float(policy["maximum_broker_weight_pct"]),
        "minimum_healthy_brokers":health.get("passed") is True,
        "automatic_write_failover_disabled":policy.get("automatic_failover_write_enabled") is False,
        "broker_write_disabled":policy.get("broker_write_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"passed":not failed,"checks":checks,"failed":failed,"maximum_broker_weight_pct_observed":max_weight}
