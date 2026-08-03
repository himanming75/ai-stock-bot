from __future__ import annotations
from pathlib import Path
from typing import Any

from parameter_optimizer.io import load_json
from parameter_optimizer.search_space import get_space
from parameter_optimizer.walk_forward import evaluate_windows
from parameter_optimizer.scoring import optimization_score, stability_gate
from strategy_lab.adapter import base_strategy_name
from v89_engine.backtest import run_strategy
from v89_engine.discovery import discover_historical_files
from v89_engine.io import load_bars

def candidate_strategy_ids(source: dict[str, Any], top_n: int) -> list[str]:
    rankings = source.get("rankings", [])
    ids = [
        str(row.get("strategy_id"))
        for row in rankings
        if row.get("strategy_id")
    ]
    if ids:
        return ids[:top_n]
    top_candidate = source.get("top_candidate", {})
    if top_candidate.get("strategy_id"):
        return [str(top_candidate["strategy_id"])]
    return ["MOMENTUM_10", "EMA_FAST_10_30", "RSI_35_65"][:top_n]

def optimize(
    root: Path,
    explicit_input: str = "",
) -> dict[str, Any]:
    policy = load_json(
        root / "release/v91_33_to_v91_64/input/optimization_policy.json"
    )
    lab_result = load_json(
        root / "release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json"
    )

    discovery = discover_historical_files(root)
    selected = Path(explicit_input) if explicit_input else (
        Path(discovery["selected"]["path"])
        if discovery.get("selected") else None
    )

    if not selected or not selected.exists():
        return {
            "stage": "V91.64",
            "stage_range": "V91.33-V91.64",
            "state": "PARAMETER_OPTIMIZATION_HISTORICAL_DATA_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    bars = load_bars(selected)
    top_n = int(policy.get("top_strategy_count", 3))
    max_combinations = int(policy.get("maximum_combinations_per_strategy", 40))
    window_count = int(policy.get("walk_forward_window_count", 4))
    strategy_ids = candidate_strategy_ids(lab_result, top_n)

    all_results = []
    for strategy_id in strategy_ids:
        base = base_strategy_name(strategy_id)
        space = get_space(base)[:max_combinations]
        for parameters in space:
            full_result = run_strategy(bars, base, parameters)
            walk = evaluate_windows(
                bars,
                base,
                parameters,
                window_count,
            )
            gate = stability_gate(full_result, walk, policy)
            all_results.append({
                "strategy_id": strategy_id,
                "base_strategy": base,
                "parameters": parameters,
                "full_result": full_result,
                "walk_forward": walk,
                "stability_gate": gate,
                "optimization_score": optimization_score(
                    full_result,
                    walk,
                ),
            })

    all_results.sort(
        key=lambda row: row["optimization_score"],
        reverse=True,
    )
    for index, row in enumerate(all_results, 1):
        row["optimization_rank"] = index

    stable = [
        row for row in all_results
        if row["stability_gate"]["passed"]
    ]
    best_stable = stable[0] if stable else None
    best_candidate = all_results[0] if all_results else None

    return {
        "stage": "V91.64",
        "stage_range": "V91.33-V91.64",
        "state": (
            "PARAMETER_OPTIMIZATION_STABLE_CANDIDATE_READY"
            if best_stable
            else "PARAMETER_OPTIMIZATION_REVIEW_REQUIRED"
        ),
        "status": "PASS",
        "historical_input": str(selected.resolve()),
        "bar_count": len(bars),
        "source_strategy_ids": strategy_ids,
        "evaluated_combination_count": len(all_results),
        "stable_combination_count": len(stable),
        "best_stable_candidate": best_stable,
        "best_candidate": best_candidate,
        "top_results": all_results[:25],
        "policy": policy,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V92_01_AI_EXPLAINABILITY_PRO",
    }
