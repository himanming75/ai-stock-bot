from __future__ import annotations
from typing import Any

DEFAULT_POLICY={
    "maximum_accounts":5,
    "maximum_positions":10,
    "maximum_gross_exposure_pct":50.0,
    "maximum_symbol_weight_pct":25.0,
    "minimum_cash_weight_pct":20.0,
    "broker_write_enabled":False,
    "live_submission_enabled":False,
}

def evaluate(portfolio:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    effective={**DEFAULT_POLICY,**(policy or {})}
    summary=portfolio.get("summary",{})
    max_symbol=max(
        [abs(float(x.get("weight_pct",0))) for x in portfolio.get("symbol_allocation",[])]
        or [0]
    )
    checks={
        "maximum_accounts":summary.get("account_count",0)<=int(effective["maximum_accounts"]),
        "maximum_positions":summary.get("position_count",0)<=int(effective["maximum_positions"]),
        "maximum_gross_exposure_pct":summary.get("gross_exposure_pct",0)<=float(effective["maximum_gross_exposure_pct"]),
        "maximum_symbol_weight_pct":max_symbol<=float(effective["maximum_symbol_weight_pct"]),
        "minimum_cash_weight_pct":summary.get("cash_weight_pct",0)>=float(effective["minimum_cash_weight_pct"]),
        "all_accounts_read_only":all(x.get("read_only") is True for x in portfolio.get("accounts",[])),
        "broker_write_disabled":effective.get("broker_write_enabled") is False,
        "live_submission_disabled":effective.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "maximum_symbol_weight_pct_observed":max_symbol,
    }
