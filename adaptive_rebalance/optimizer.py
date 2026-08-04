from __future__ import annotations
from typing import Any
from adaptive_rebalance.costs import estimate_cost
from adaptive_rebalance.thresholds import adaptive_threshold

def optimize_adjustments(
    control_result: dict[str, Any],
    regime_multiplier_value: float,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    base_trigger = float(policy.get("base_rebalance_trigger_pct", 3.0))
    fraction = float(policy.get("base_incremental_fraction", 0.5))
    minimum_fraction = float(policy.get("minimum_incremental_fraction", 0.2))
    maximum_fraction = float(policy.get("maximum_incremental_fraction", 0.8))
    minimum_net_benefit = float(policy.get("minimum_net_benefit", 25.0))
    metrics = {
        str(row.get("strategy_id")): row
        for row in policy.get("strategy_metrics", [])
        if row.get("strategy_id")
    }

    rows = []
    for source in control_result.get("snapshot", {}).get("drift_rows", []):
        strategy_id = str(source.get("strategy_id", ""))
        if not strategy_id or strategy_id == "CASH":
            continue
        metric = metrics.get(strategy_id, {})
        volatility_pct = float(metric.get("observed_volatility_pct", 2.0))
        cost_bps = (
            float(policy.get("commission_bps", 0.0))
            + float(policy.get("slippage_bps", 5.0))
            + float(policy.get("spread_bps", 2.0))
        )
        threshold = adaptive_threshold(
            base_trigger,
            volatility_pct,
            regime_multiplier_value,
            cost_bps,
            policy,
        )
        absolute_drift = float(source.get("absolute_drift_pct", 0.0))
        if absolute_drift < threshold["adaptive_trigger_pct"]:
            rows.append({
                "strategy_id": strategy_id,
                "state": "SKIPPED_ADAPTIVE_THRESHOLD",
                "adaptive_trigger_pct": threshold["adaptive_trigger_pct"],
                "absolute_drift_pct": round(absolute_drift, 6),
                "submission_allowed": False,
            })
            continue

        severity = absolute_drift / max(1e-9, threshold["adaptive_trigger_pct"])
        adaptive_fraction = max(
            minimum_fraction,
            min(maximum_fraction, fraction * min(1.5, severity)),
        )
        equity = float(control_result.get("account_equity", 0.0))
        requested_notional = equity * absolute_drift / 100.0 * adaptive_fraction
        cost = estimate_cost(requested_notional, policy)
        estimated_benefit = requested_notional * absolute_drift / 100.0
        net_benefit = estimated_benefit - cost["estimated_cost"]

        state = "OPTIMIZED"
        if net_benefit < minimum_net_benefit:
            state = "SKIPPED_COST_BENEFIT"

        rows.append({
            "strategy_id": strategy_id,
            "side": "SELL" if float(source.get("drift_pct", 0.0)) > 0 else "BUY",
            "drift_pct": round(float(source.get("drift_pct", 0.0)), 6),
            "absolute_drift_pct": round(absolute_drift, 6),
            "adaptive_trigger_pct": threshold["adaptive_trigger_pct"],
            "adaptive_fraction": round(adaptive_fraction, 6),
            "requested_notional": round(requested_notional, 6),
            "estimated_benefit": round(estimated_benefit, 6),
            "estimated_cost": cost["estimated_cost"],
            "net_benefit": round(net_benefit, 6),
            "state": state,
            "submission_allowed": False,
        })
    return rows
