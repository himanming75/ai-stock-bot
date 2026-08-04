from __future__ import annotations
from typing import Any

def evaluate_loss_limits(
    policy: dict[str, Any],
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    daily=float(telemetry.get("daily_pnl",0.0))
    weekly=float(telemetry.get("weekly_pnl",0.0))
    equity=float(telemetry.get("account_equity",0.0))
    daily_limit=-abs(equity*float(policy.get("maximum_daily_loss_pct",2.0))/100.0)
    weekly_limit=-abs(equity*float(policy.get("maximum_weekly_loss_pct",5.0))/100.0)
    checks={
        "daily_loss_within_limit":daily>=daily_limit,
        "weekly_loss_within_limit":weekly>=weekly_limit,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "daily_pnl":daily,
        "weekly_pnl":weekly,
        "daily_loss_limit":round(daily_limit,2),
        "weekly_loss_limit":round(weekly_limit,2),
        "checks":checks,
        "failed":failed,
        "passed":not failed,
    }
