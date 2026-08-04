from __future__ import annotations
from typing import Any
from risk_engine_v2.metrics import drawdown,daily_loss,position_size

def evaluate(policy:dict[str,Any],state:dict[str,Any],candidate:dict[str,Any],kill_switch:dict[str,Any])->dict[str,Any]:
    dd=drawdown(state.get("peak_equity"),state.get("current_equity"))
    dl=daily_loss(state.get("day_start_equity"),state.get("current_equity"))
    consecutive=int(state.get("consecutive_losses",0) or 0)
    atr=float(candidate.get("atr_pct",0) or 0)
    symbol_weight=float(candidate.get("projected_symbol_weight_pct",0) or 0)
    sector_weight=float(candidate.get("projected_sector_weight_pct",0) or 0)
    correlation=float(candidate.get("maximum_correlation",0) or 0)
    sizing=position_size(
        state.get("current_equity",0),policy["risk_per_trade_pct"],
        candidate.get("entry_price",0),candidate.get("stop_price",0),
        int(policy["maximum_position_quantity"]),float(policy["maximum_position_notional"])
    )
    checks={
      "kill_switch_clear":kill_switch.get("enabled") is False,
      "drawdown_within_limit":dd<policy["maximum_drawdown_pct"],
      "daily_loss_within_limit":dl<policy["maximum_daily_loss_pct"],
      "circuit_breaker_clear":consecutive<policy["maximum_consecutive_losses"],
      "volatility_within_limit":atr<=policy["maximum_atr_pct"],
      "symbol_weight_within_limit":symbol_weight<=policy["maximum_symbol_weight_pct"],
      "sector_weight_within_limit":sector_weight<=policy["maximum_sector_weight_pct"],
      "correlation_within_limit":correlation<=policy["maximum_correlation"],
      "position_size_positive":sizing["quantity"]>0,
      "broker_write_disabled":policy.get("broker_write_enabled") is False,
      "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
      "passed":not failed,
      "checks":checks,
      "failed":failed,
      "metrics":{
        "drawdown_pct":dd,
        "daily_loss_pct":dl,
        "consecutive_losses":consecutive,
        "atr_pct":atr,
        "projected_symbol_weight_pct":symbol_weight,
        "projected_sector_weight_pct":sector_weight,
        "maximum_correlation":correlation,
      },
      "position_size":sizing,
    }
