
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import importlib.util
import math

MIN_INTERPRETATION_SAMPLE = 10


def _num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _net_pnl(stress_module, trades, scenario):
    stressed = [
        stress_module._stress_trade(trade, scenario)
        for trade in trades
    ]
    stats = stress_module._stats(stressed)
    return stats.get("net_realized_pnl"), stats, stressed


def _search_boundary(
    stress_module,
    trades,
    parameter_name,
    low,
    high,
    fixed=None,
    iterations=36,
):
    fixed = dict(fixed or {})

    def scenario(value):
        payload = {
            "id": f"BOUNDARY_{parameter_name}",
            "label": "Boundary",
            "friction_bps_per_leg": 0.0,
            "winner_haircut_pct": 0.0,
            "loser_amplification_pct": 0.0,
        }
        payload.update(fixed)
        payload[parameter_name] = float(value)
        return payload

    low_pnl, _, _ = _net_pnl(stress_module, trades, scenario(low))
    high_pnl, _, _ = _net_pnl(stress_module, trades, scenario(high))

    if low_pnl is None:
        return {"status": "NO_NUMERIC_PNL", "boundary": None}

    if low_pnl <= 0:
        return {
            "status": "FAILED_AT_BASELINE",
            "boundary": low,
            "baseline_pnl": low_pnl,
        }

    if high_pnl is None or high_pnl > 0:
        return {
            "status": "NOT_REACHED_WITHIN_SEARCH_RANGE",
            "boundary": None,
            "search_high": high,
            "pnl_at_search_high": high_pnl,
        }

    lo = float(low)
    hi = float(high)
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        pnl, _, _ = _net_pnl(stress_module, trades, scenario(mid))
        if pnl is None:
            break
        if pnl > 0:
            lo = mid
        else:
            hi = mid

    boundary = hi
    boundary_pnl, boundary_stats, _ = _net_pnl(
        stress_module, trades, scenario(boundary)
    )
    return {
        "status": "FOUND",
        "boundary": boundary,
        "pnl_at_boundary": boundary_pnl,
        "stats_at_boundary": boundary_stats,
    }


def _winner_haircut_boundary(stress_module, trades):
    if not any((_num(t.get("pnl")) or 0) > 0 for t in trades):
        return {"status": "NO_WINNERS_OBSERVED", "boundary": None}
    return _search_boundary(
        stress_module,
        trades,
        "winner_haircut_pct",
        0.0,
        100.0,
    )


def _loss_amplification_boundary(stress_module, trades):
    if not any((_num(t.get("pnl")) or 0) < 0 for t in trades):
        return {
            "status": "UNOBSERVED_NO_LOSING_TRADES",
            "boundary": None,
        }
    return _search_boundary(
        stress_module,
        trades,
        "loser_amplification_pct",
        0.0,
        1000.0,
    )


def _friction_boundary(stress_module, trades):
    return _search_boundary(
        stress_module,
        trades,
        "friction_bps_per_leg",
        0.0,
        500.0,
    )


def _profit_factor_boundary(stress_module, trades):
    def evaluate(value):
        scenario = {
            "id": "PF_BOUNDARY",
            "label": "PF Boundary",
            "friction_bps_per_leg": float(value),
            "winner_haircut_pct": 0.0,
            "loser_amplification_pct": 0.0,
        }
        _, stats, _ = _net_pnl(stress_module, trades, scenario)
        pf = stats.get("profit_factor")
        if pf == "INF":
            return False, pf
        pf_num = _num(pf)
        return (pf_num is not None and pf_num <= 1.0), pf

    bad0, pf0 = evaluate(0.0)
    if bad0:
        return {
            "status": "FAILED_AT_BASELINE",
            "boundary_bps_per_leg": 0.0,
            "profit_factor": pf0,
        }

    bad_high, pf_high = evaluate(500.0)
    if not bad_high:
        return {
            "status": "NOT_REACHED_WITHIN_SEARCH_RANGE",
            "boundary_bps_per_leg": None,
            "search_high": 500.0,
            "profit_factor_at_search_high": pf_high,
        }

    lo, hi = 0.0, 500.0
    last_pf = pf_high
    for _ in range(36):
        mid = (lo + hi) / 2.0
        bad, pf = evaluate(mid)
        last_pf = pf
        if bad:
            hi = mid
        else:
            lo = mid

    return {
        "status": "FOUND",
        "boundary_bps_per_leg": hi,
        "profit_factor_at_boundary": last_pf,
    }


def _readiness_boundary(root, stress_module, trades):
    readiness_module = _load_module(
        root / "dashboard" / "strategy_readiness_v3_12.py",
        "v315_readiness",
    )
    diagnostics_module = _load_module(
        root / "dashboard" / "performance_diagnostics_v3_11.py",
        "v315_diagnostics",
    )

    def evaluate(friction):
        scenario = {
            "id": "READINESS_BOUNDARY",
            "label": "Readiness Boundary",
            "friction_bps_per_leg": float(friction),
            "winner_haircut_pct": 0.0,
            "loser_amplification_pct": 0.0,
        }
        _, stats, stressed = _net_pnl(stress_module, trades, scenario)
        diagnostics = diagnostics_module.build_performance_diagnostics(stressed)
        return readiness_module.build_strategy_readiness({
            "historical": stats,
            "performance_diagnostics": diagnostics,
        })

    baseline = evaluate(0.0)

    if len(trades) < MIN_INTERPRETATION_SAMPLE:
        return {
            "status": "INSUFFICIENT_SAMPLE_BASELINE_NOT_READY",
            "boundary_bps_per_leg": None,
            "baseline_readiness_status": baseline.get("status"),
            "baseline_score": baseline.get("overall_score"),
        }

    if baseline.get("status") not in (
        "READY_FOR_EXTENDED_PAPER",
        "CONDITIONAL",
    ):
        return {
            "status": "BASELINE_ALREADY_NOT_READY",
            "boundary_bps_per_leg": 0.0,
            "baseline_readiness_status": baseline.get("status"),
            "baseline_score": baseline.get("overall_score"),
        }

    lo, hi = 0.0, 500.0
    high_result = evaluate(hi)
    if high_result.get("status") in (
        "READY_FOR_EXTENDED_PAPER",
        "CONDITIONAL",
    ):
        return {
            "status": "NOT_REACHED_WITHIN_SEARCH_RANGE",
            "boundary_bps_per_leg": None,
            "search_high": hi,
        }

    for _ in range(36):
        mid = (lo + hi) / 2.0
        result = evaluate(mid)
        if result.get("status") in (
            "READY_FOR_EXTENDED_PAPER",
            "CONDITIONAL",
        ):
            lo = mid
        else:
            hi = mid

    result = evaluate(hi)
    return {
        "status": "FOUND",
        "boundary_bps_per_leg": hi,
        "readiness_status_at_boundary": result.get("status"),
        "readiness_score_at_boundary": result.get("overall_score"),
    }


def _normalized_boundary_score(result, reference_max):
    boundary = _num(result.get("boundary"))
    if boundary is None:
        boundary = _num(result.get("boundary_bps_per_leg"))
    if boundary is None:
        return None
    return max(0.0, min(100.0, (boundary / reference_max) * 100.0))


def build_strategy_robustness(root: Path, canonical_trades: list[dict]):
    trades = [
        deepcopy(t)
        for t in canonical_trades
        if _num(t.get("pnl")) is not None
    ]

    stress_module = _load_module(
        root / "dashboard" / "strategy_stress_test_v3_14.py",
        "v315_stress",
    )

    friction = _friction_boundary(stress_module, trades)
    winner_haircut = _winner_haircut_boundary(stress_module, trades)
    loss_amplification = _loss_amplification_boundary(stress_module, trades)
    pf_boundary = _profit_factor_boundary(stress_module, trades)
    readiness_boundary = _readiness_boundary(root, stress_module, trades)

    components = []
    friction_score = _normalized_boundary_score(friction, 50.0)
    haircut_score = _normalized_boundary_score(winner_haircut, 50.0)
    loss_score = _normalized_boundary_score(loss_amplification, 100.0)

    for score in (friction_score, haircut_score, loss_score):
        if score is not None:
            components.append(score)

    raw_robustness = (
        sum(components) / len(components)
        if components else 0.0
    )

    sample_status = (
        "PASS_SAMPLE"
        if len(trades) >= MIN_INTERPRETATION_SAMPLE
        else "INSUFFICIENT_SAMPLE"
    )
    displayed = raw_robustness
    if sample_status == "INSUFFICIENT_SAMPLE":
        displayed = min(displayed, 49.0)

    return {
        "stage": "V3.15_STRATEGY_ROBUSTNESS_FAILURE_BOUNDARY",
        "status": (
            "PASS"
            if sample_status == "PASS_SAMPLE"
            else "PASS_INSUFFICIENT_SAMPLE"
        ),
        "sample_status": sample_status,
        "canonical_numeric_trade_count": len(trades),
        "minimum_interpretation_sample": MIN_INTERPRETATION_SAMPLE,
        "robustness_score": round(displayed, 2),
        "raw_robustness_score": round(raw_robustness, 2),
        "failure_boundaries": {
            "break_even_friction_bps_per_leg": friction,
            "winner_haircut_pct": winner_haircut,
            "loss_amplification_pct": loss_amplification,
            "profit_factor_one_friction_bps_per_leg": pf_boundary,
            "readiness_failure_friction_bps_per_leg": readiness_boundary,
        },
        "observability": {
            "has_winners": any(
                (_num(t.get("pnl")) or 0) > 0 for t in trades
            ),
            "has_losses": any(
                (_num(t.get("pnl")) or 0) < 0 for t in trades
            ),
        },
        "interpretation": (
            "Failure boundaries are descriptive only because fewer than 10 canonical trades are available."
            if sample_status == "INSUFFICIENT_SAMPLE"
            else "Failure boundaries are Paper-validation diagnostics only and are not Live approval."
        ),
        "contracts": {
            "simulation_only": True,
            "canonical_trade_copy_only": True,
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
