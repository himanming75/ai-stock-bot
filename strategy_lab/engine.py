from __future__ import annotations
from pathlib import Path
from typing import Any

from strategy_lab.registry import StrategyRegistry
from strategy_lab.adapter import base_strategy_name
from strategy_lab.scoring import champion_score
from v89_engine.backtest import run_strategy, buy_hold
from v89_engine.discovery import discover_historical_files
from v89_engine.io import load_bars, load_json
from v89_engine.gates import evaluate

def run_lab(root: Path, explicit_input: str = "") -> dict[str, Any]:
    registry = StrategyRegistry()
    registry.register_defaults()

    discovery = discover_historical_files(root)
    selected = Path(explicit_input) if explicit_input else (
        Path(discovery["selected"]["path"]) if discovery.get("selected") else None
    )

    if not selected or not selected.exists():
        return {
            "stage": "V91.32",
            "stage_range": "V91.01-V91.32",
            "state": "STRATEGY_LAB_HISTORICAL_DATA_REQUIRED",
            "status": "PASS",
            "registry": [item.to_dict() for item in registry.all()],
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    bars = load_bars(selected)
    benchmark = buy_hold(bars)
    validation_file = load_json(
        root / "release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json"
    )
    validation = validation_file.get("validation", {})
    validation_summary = {
        "overfit_risk_score": validation.get("overfit", {}).get("overfit_risk_score", 0),
        "positive_window_pct": validation.get("walk_forward", {}).get("positive_window_pct", 100),
    }

    results = []
    for definition in registry.enabled():
        metrics = run_strategy(
            bars,
            base_strategy_name(definition.strategy_id),
            definition.parameters,
        )
        metrics["strategy_id"] = definition.strategy_id
        metrics["strategy_name"] = definition.name
        metrics["category"] = definition.category
        metrics["parameters"] = definition.parameters
        metrics["gate"] = evaluate(
            metrics,
            validation_summary,
            benchmark["total_return_pct"],
        )
        metrics["champion_score"] = champion_score(metrics)
        results.append(metrics)

    results.sort(key=lambda row: row["champion_score"], reverse=True)
    for index, row in enumerate(results, 1):
        row["lab_rank"] = index

    approved = [row for row in results if row["gate"]["approved"]]
    champion = approved[0] if approved else None
    candidate = results[0] if results else None

    return {
        "stage": "V91.32",
        "stage_range": "V91.01-V91.32",
        "state": (
            "ULTIMATE_STRATEGY_LAB_CHAMPION_READY"
            if champion
            else "ULTIMATE_STRATEGY_LAB_REVIEW_REQUIRED"
        ),
        "status": "PASS",
        "historical_input": str(selected.resolve()),
        "bar_count": len(bars),
        "registered_strategy_count": len(registry.all()),
        "executed_strategy_count": len(results),
        "approved_strategy_count": len(approved),
        "benchmark": benchmark,
        "champion": champion,
        "top_candidate": candidate,
        "rankings": results,
        "registry": [item.to_dict() for item in registry.all()],
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V91_33_PARAMETER_OPTIMIZATION",
    }
