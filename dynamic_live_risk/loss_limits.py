from __future__ import annotations
from typing import Any

def evaluate(account:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    equity=float(account.get("equity",0.0))
    daily=float(policy.get("current_daily_pnl",0.0))
    weekly=float(policy.get("current_weekly_pnl",0.0))
    daily_limit=-abs(equity*float(policy.get("maximum_daily_loss_pct",1.0))/100.0)
    weekly_limit=-abs(equity*float(policy.get("maximum_weekly_loss_pct",3.0))/100.0)
    checks={
        "daily_loss_within_limit":daily>=daily_limit,
        "weekly_loss_within_limit":weekly>=weekly_limit,
        "consecutive_loss_limit_clear":int(policy.get("current_consecutive_losses",0))<int(policy.get("maximum_consecutive_losses",3)),
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "current_daily_pnl":daily,
        "current_weekly_pnl":weekly,
        "daily_loss_limit":round(daily_limit,2),
        "weekly_loss_limit":round(weekly_limit,2),
        "checks":checks,
        "failed":failed,
        "passed":not failed,
    }
