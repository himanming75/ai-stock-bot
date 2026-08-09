
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import importlib.util
import math

SCENARIOS = (
    {
        "id": "BASELINE",
        "label": "Baseline",
        "friction_bps_per_leg": 0.0,
        "winner_haircut_pct": 0.0,
        "loser_amplification_pct": 0.0,
    },
    {
        "id": "MILD",
        "label": "Mild Stress",
        "friction_bps_per_leg": 2.0,
        "winner_haircut_pct": 5.0,
        "loser_amplification_pct": 5.0,
    },
    {
        "id": "MODERATE",
        "label": "Moderate Stress",
        "friction_bps_per_leg": 5.0,
        "winner_haircut_pct": 10.0,
        "loser_amplification_pct": 15.0,
    },
    {
        "id": "SEVERE",
        "label": "Severe Stress",
        "friction_bps_per_leg": 10.0,
        "winner_haircut_pct": 20.0,
        "loser_amplification_pct": 30.0,
    },
)

def _num(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None

def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _round_trip_friction(trade: dict, bps_per_leg: float):
    qty = _num(trade.get("qty"))
    entry = _num(trade.get("entry_price"))
    exit_price = _num(trade.get("exit_price"))
    if qty is None or entry is None or exit_price is None:
        return 0.0
    entry_notional = abs(qty * entry)
    exit_notional = abs(qty * exit_price)
    return (entry_notional + exit_notional) * float(bps_per_leg) / 10000.0

def _stress_trade(trade: dict, scenario: dict):
    stressed = deepcopy(trade)
    original_pnl = _num(trade.get("pnl"))

    if original_pnl is None:
        stressed["stress_original_pnl"] = None
        stressed["stress_friction_cost"] = None
        stressed["stress_adjusted_pnl"] = None
        return stressed

    if original_pnl > 0:
        base_adjusted = original_pnl * (
            1.0 - scenario["winner_haircut_pct"] / 100.0
        )
    elif original_pnl < 0:
        base_adjusted = original_pnl * (
            1.0 + scenario["loser_amplification_pct"] / 100.0
        )
    else:
        base_adjusted = 0.0

    friction = _round_trip_friction(
        trade,
        scenario["friction_bps_per_leg"],
    )
    stressed_pnl = base_adjusted - friction

    stressed["stress_original_pnl"] = original_pnl
    stressed["stress_friction_cost"] = friction
    stressed["stress_adjusted_pnl"] = stressed_pnl
    stressed["pnl"] = stressed_pnl
    stressed["realized_pl"] = stressed_pnl
    stressed["stress_scenario"] = scenario["id"]
    return stressed

def _stats(trades):
    pnls = [
        _num(t.get("pnl"))
        for t in trades
        if _num(t.get("pnl")) is not None
    ]
    wins = [v for v in pnls if v > 0]
    losses = [v for v in pnls if v < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    elif gross_profit > 0:
        pf = "INF"
    else:
        pf = None

    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    curve = []

    for trade in trades:
        pnl = _num(trade.get("pnl"))
        if pnl is None:
            continue
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        curve.append({
            "time": trade.get("exit_time") or trade.get("time"),
            "value": equity,
        })

    return {
        "numeric_trade_count": len(pnls),
        "net_realized_pnl": sum(pnls) if pnls else None,
        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len([v for v in pnls if v == 0]),
        "win_rate": len(wins) / len(pnls) if pnls else None,
        "gross_profit": gross_profit if pnls else None,
        "gross_loss": gross_loss if pnls else None,
        "profit_factor": pf,
        "average_trade": sum(pnls) / len(pnls) if pnls else None,
        "average_win": sum(wins) / len(wins) if wins else None,
        "average_loss": sum(losses) / len(losses) if losses else None,
        "best_trade": max(pnls) if pnls else None,
        "worst_trade": min(pnls) if pnls else None,
        "max_realized_drawdown": max_dd if pnls else None,
        "cumulative_realized_pnl": curve,
    }

def _scenario_result(root: Path, trades: list[dict], scenario: dict):
    stressed_trades = [_stress_trade(trade, scenario) for trade in trades]
    stats = _stats(stressed_trades)

    diagnostics_module = _load_module(
        root / "dashboard" / "performance_diagnostics_v3_11.py",
        f"stress_diag_{scenario['id']}",
    )
    diagnostics = diagnostics_module.build_performance_diagnostics(
        stressed_trades
    )

    readiness_module = _load_module(
        root / "dashboard" / "strategy_readiness_v3_12.py",
        f"stress_ready_{scenario['id']}",
    )
    readiness = readiness_module.build_strategy_readiness({
        "historical": stats,
        "performance_diagnostics": diagnostics,
    })

    total_friction = sum(
        float(t.get("stress_friction_cost") or 0.0)
        for t in stressed_trades
    )
    original_total = sum(
        float(t.get("stress_original_pnl") or 0.0)
        for t in stressed_trades
        if t.get("stress_original_pnl") is not None
    )
    stressed_total = stats.get("net_realized_pnl")
    pnl_degradation = (
        original_total - stressed_total
        if stressed_total is not None
        else None
    )

    sample_status = (
        "PASS_SAMPLE"
        if stats["numeric_trade_count"] >= 10
        else "INSUFFICIENT_SAMPLE"
    )

    return {
        "scenario": scenario,
        "sample_status": sample_status,
        "stats": stats,
        "diagnostics": diagnostics,
        "readiness": readiness,
        "total_friction_cost": total_friction,
        "original_net_pnl_reference": original_total,
        "pnl_degradation_vs_original": pnl_degradation,
        "stressed_trade_preview": list(reversed(stressed_trades[-20:])),
    }

def build_strategy_stress_test(root: Path, canonical_trades: list[dict]):
    numeric = [
        deepcopy(t)
        for t in canonical_trades
        if _num(t.get("pnl")) is not None
    ]

    scenarios = [
        _scenario_result(root, numeric, scenario)
        for scenario in SCENARIOS
    ]

    baseline = scenarios[0] if scenarios else None
    severe = scenarios[-1] if scenarios else None

    baseline_pnl = (
        (baseline or {}).get("stats", {}).get("net_realized_pnl")
    )
    severe_pnl = (
        (severe or {}).get("stats", {}).get("net_realized_pnl")
    )

    severe_degradation_pct = None
    if (
        baseline_pnl is not None
        and severe_pnl is not None
        and baseline_pnl != 0
    ):
        severe_degradation_pct = (
            (baseline_pnl - severe_pnl)
            / abs(baseline_pnl)
        )

    return {
        "stage": "V3.14_STRATEGY_STRESS_TEST",
        "status": (
            "PASS"
            if len(numeric) >= 10
            else "PASS_INSUFFICIENT_SAMPLE"
        ),
        "sample_status": (
            "PASS_SAMPLE"
            if len(numeric) >= 10
            else "INSUFFICIENT_SAMPLE"
        ),
        "canonical_numeric_trade_count": len(numeric),
        "minimum_interpretation_sample": 10,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "severe_degradation_pct": severe_degradation_pct,
        "interpretation": (
            "Stress results are descriptive only because the canonical sample is below 10 trades."
            if len(numeric) < 10
            else "Stress results may be used as Paper-validation diagnostics only."
        ),
        "contracts": {
            "simulation_only": True,
            "canonical_trades_modified": False,
            "canonical_runtime_files_modified": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
            "automatic_promotion": False,
            "live_approval": False,
            "duplicate_engine_created": False,
        },
    }
