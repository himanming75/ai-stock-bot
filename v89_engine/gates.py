from __future__ import annotations

DEFAULT_THRESHOLDS={
 "minimum_trades":2,"minimum_profit_factor":1.0,"maximum_drawdown_pct":35.0,
 "minimum_sharpe_ratio":0.0,"minimum_excess_return_pct":-10.0,
 "maximum_overfit_risk_score":75.0,"minimum_positive_window_pct":25.0
}

def evaluate(metrics, validation, benchmark_return, thresholds=None):
    t={**DEFAULT_THRESHOLDS,**(thresholds or {})}
    excess=metrics["total_return_pct"]-benchmark_return
    checks={
      "minimum_trades":metrics["total_trades"]>=t["minimum_trades"],
      "minimum_profit_factor":metrics["profit_factor"]>=t["minimum_profit_factor"],
      "maximum_drawdown":metrics["maximum_drawdown_pct"]<=t["maximum_drawdown_pct"],
      "minimum_sharpe":metrics["sharpe_ratio"]>=t["minimum_sharpe_ratio"],
      "minimum_excess_return":excess>=t["minimum_excess_return_pct"],
      "maximum_overfit_risk":float(validation.get("overfit_risk_score",0))<=t["maximum_overfit_risk_score"],
      "minimum_positive_windows":float(validation.get("positive_window_pct",100))>=t["minimum_positive_window_pct"],
    }
    return {"approved":all(checks.values()),"checks":checks,"failed":[k for k,v in checks.items() if not v],
            "excess_return_pct":round(excess,4),"thresholds":t}
