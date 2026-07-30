from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


VERSION = "73.0"
SCHEMA_VERSION = "v73.0.parameter_optimization.1"
SUPPORTED_V72_SCHEMA = "v72.0.strategy_revision_requalification.1"


class OptimizationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OptimizationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OptimizationError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise OptimizationError("top-level JSON must be an object")
    return data


def validate_v72(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise OptimizationError("V72 status must be PASS")
    if report.get("schema_version") != SUPPORTED_V72_SCHEMA:
        raise OptimizationError("unsupported V72 schema_version")
    if report.get("network_used") is not False:
        raise OptimizationError("V72 network_used must be false")
    if report.get("approved_for_live") is not False:
        raise OptimizationError("V72 approved_for_live must be false")
    if report.get("requires_strategy_revision") is not True:
        raise OptimizationError("V72 must require strategy revision")
    if not isinstance(report.get("recommendations"), list):
        raise OptimizationError("V72 recommendations must be a list")


def validate_baseline(parameters: Dict[str, Any]) -> None:
    required = {
        "signal_threshold": (int, float),
        "stop_loss_pct": (int, float),
        "take_profit_pct": (int, float),
        "min_volume_ratio": (int, float),
        "cooldown_bars": int,
    }
    for key, expected_type in required.items():
        if key not in parameters:
            raise OptimizationError(f"missing baseline parameter: {key}")
        if not isinstance(parameters[key], expected_type) or isinstance(parameters[key], bool):
            raise OptimizationError(f"invalid baseline parameter type: {key}")

    if not 0 < float(parameters["signal_threshold"]) <= 1:
        raise OptimizationError("signal_threshold must be in (0, 1]")
    if not 0 < float(parameters["stop_loss_pct"]) < 1:
        raise OptimizationError("stop_loss_pct must be in (0, 1)")
    if not 0 < float(parameters["take_profit_pct"]) < 1:
        raise OptimizationError("take_profit_pct must be in (0, 1)")
    if float(parameters["min_volume_ratio"]) <= 0:
        raise OptimizationError("min_volume_ratio must be positive")
    if int(parameters["cooldown_bars"]) < 0:
        raise OptimizationError("cooldown_bars must be non-negative")


def clamp(value: float, low: float, high: float, digits: int = 6) -> float:
    return round(min(max(value, low), high), digits)


def recommendation_codes(report: Dict[str, Any]) -> set[str]:
    return {
        str(item.get("code"))
        for item in report.get("recommendations", [])
        if isinstance(item, dict)
    }


def build_search_space(
    v72_report: Dict[str, Any],
    baseline: Dict[str, Any],
) -> Dict[str, List[Any]]:
    validate_v72(v72_report)
    validate_baseline(baseline)

    codes = recommendation_codes(v72_report)

    signal = float(baseline["signal_threshold"])
    stop = float(baseline["stop_loss_pct"])
    target = float(baseline["take_profit_pct"])
    volume = float(baseline["min_volume_ratio"])
    cooldown = int(baseline["cooldown_bars"])

    search_space: Dict[str, List[Any]] = {
        "signal_threshold": [round(signal, 6)],
        "stop_loss_pct": [round(stop, 6)],
        "take_profit_pct": [round(target, 6)],
        "min_volume_ratio": [round(volume, 6)],
        "cooldown_bars": [cooldown],
    }

    if "REV-ENTRY-QUALITY" in codes:
        search_space["signal_threshold"] = sorted(set([
            clamp(signal, 0.01, 1.0),
            clamp(signal + 0.05, 0.01, 1.0),
            clamp(signal + 0.10, 0.01, 1.0),
        ]))
        search_space["min_volume_ratio"] = sorted(set([
            clamp(volume, 0.1, 10.0),
            clamp(volume + 0.25, 0.1, 10.0),
            clamp(volume + 0.50, 0.1, 10.0),
        ]))

    if "REV-LOSS-CONTROL" in codes:
        search_space["stop_loss_pct"] = sorted(set([
            clamp(stop * 0.75, 0.001, 0.50),
            clamp(stop, 0.001, 0.50),
            clamp(stop * 1.10, 0.001, 0.50),
        ]))
        search_space["cooldown_bars"] = sorted(set([
            max(0, cooldown),
            max(0, cooldown + 2),
            max(0, cooldown + 4),
        ]))

    if "REV-EDGE-RECOVERY" in codes:
        search_space["take_profit_pct"] = sorted(set([
            clamp(target * 0.90, 0.001, 0.75),
            clamp(target, 0.001, 0.75),
            clamp(target * 1.15, 0.001, 0.75),
        ]))

    return search_space


def candidate_id(parameters: Dict[str, Any]) -> str:
    return "CAND-" + sha256_of(parameters)[:12].upper()


def distance_score(candidate: Dict[str, Any], baseline: Dict[str, Any]) -> float:
    parts = []
    for key in [
        "signal_threshold",
        "stop_loss_pct",
        "take_profit_pct",
        "min_volume_ratio",
    ]:
        base = float(baseline[key])
        cand = float(candidate[key])
        parts.append(abs(cand - base) / max(abs(base), 1e-9))
    parts.append(
        abs(int(candidate["cooldown_bars"]) - int(baseline["cooldown_bars"]))
        / max(int(baseline["cooldown_bars"]), 1)
    )
    return round(sum(parts), 6)


def heuristic_priority(
    parameters: Dict[str, Any],
    baseline: Dict[str, Any],
    codes: set[str],
) -> float:
    score = 100.0

    if "REV-ENTRY-QUALITY" in codes:
        score += (float(parameters["signal_threshold"]) - float(baseline["signal_threshold"])) * 80
        score += (float(parameters["min_volume_ratio"]) - float(baseline["min_volume_ratio"])) * 10

    if "REV-LOSS-CONTROL" in codes:
        if float(parameters["stop_loss_pct"]) < float(baseline["stop_loss_pct"]):
            score += 8
        score += min(
            int(parameters["cooldown_bars"]) - int(baseline["cooldown_bars"]),
            4,
        )

    if "REV-EDGE-RECOVERY" in codes:
        risk_reward = float(parameters["take_profit_pct"]) / float(parameters["stop_loss_pct"])
        score += min(risk_reward, 5.0) * 2

    score -= distance_score(parameters, baseline) * 3
    return round(score, 6)


def generate_candidates(
    search_space: Dict[str, List[Any]],
    baseline: Dict[str, Any],
    codes: set[str],
    max_candidates: int,
) -> List[Dict[str, Any]]:
    if max_candidates < 1:
        raise OptimizationError("max_candidates must be at least 1")

    keys = [
        "signal_threshold",
        "stop_loss_pct",
        "take_profit_pct",
        "min_volume_ratio",
        "cooldown_bars",
    ]
    combinations = itertools.product(*(search_space[key] for key in keys))
    candidates = []

    for values in combinations:
        params = dict(zip(keys, values))
        candidates.append({
            "candidate_id": candidate_id(params),
            "parameters": params,
            "heuristic_priority_score": heuristic_priority(params, baseline, codes),
            "baseline_distance_score": distance_score(params, baseline),
            "evaluation_state": "PENDING_BACKTEST",
            "approved_for_live": False,
        })

    candidates.sort(
        key=lambda item: (
            -item["heuristic_priority_score"],
            item["baseline_distance_score"],
            item["candidate_id"],
        )
    )

    selected = candidates[:max_candidates]
    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
    return selected


def build_optimization_plan(
    v72_report: Dict[str, Any],
    baseline: Dict[str, Any],
    max_candidates: int = 24,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_v72(v72_report)
    validate_baseline(baseline)

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    codes = recommendation_codes(v72_report)
    search_space = build_search_space(v72_report, baseline)
    total_combinations = 1
    for values in search_space.values():
        total_combinations *= len(values)

    candidates = generate_candidates(
        search_space=search_space,
        baseline=baseline,
        codes=codes,
        max_candidates=max_candidates,
    )

    report = {
        "status": "PASS",
        "decision": "parameter_optimization_plan_created",
        "optimization_state": "CANDIDATES_READY",
        "created_at": created_at,
        "champion_strategy": v72_report.get("champion_strategy"),
        "revision_id": v72_report.get("revision_id"),
        "baseline_parameters": baseline,
        "recommendation_codes": sorted(codes),
        "search_space": search_space,
        "total_search_combinations": total_combinations,
        "selected_candidate_count": len(candidates),
        "max_candidates": max_candidates,
        "candidates": candidates,
        "evaluation_contract": {
            "required_input_per_candidate": [
                "paper_trade_report",
                "v68_analytics_report",
                "v70_walk_forward_report",
            ],
            "minimum_promotion_rules": {
                "v68_quality_gate": "APPROVE",
                "v70_validation_state": "APPROVED",
                "v70_requires_monte_carlo_validation": True,
                "approved_for_live": False,
            },
            "ranking_note": (
                "heuristic_priority_score only orders candidates for testing; "
                "it is not a performance result and cannot approve a strategy."
            ),
        },
        "next_step": {
            "version": "73.1",
            "action": "execute_offline_candidate_backtests",
            "then": [
                "run_v68_analytics",
                "run_v70_walk_forward_validation",
                "select_surviving_candidate",
                "run_v71_monte_carlo_validation",
            ],
        },
        "requires_offline_backtest": True,
        "approved_for_live": False,
        "network_used": False,
        "source_v72_report_sha256": v72_report.get(
            "strategy_revision_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }

    report["candidate_set_sha256"] = sha256_of(report["candidates"])
    report["parameter_optimization_report_sha256"] = sha256_of(report)
    return report


def run(
    revision_path: Path,
    baseline_path: Path,
    output_path: Path,
    max_candidates: int,
) -> Dict[str, Any]:
    revision = read_json(revision_path)
    baseline_doc = read_json(baseline_path)
    baseline = baseline_doc.get("parameters", baseline_doc)
    if not isinstance(baseline, dict):
        raise OptimizationError("baseline parameters must be an object")

    result = build_optimization_plan(
        revision,
        baseline,
        max_candidates=max_candidates,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V73 Parameter Optimization Framework"
    )
    parser.add_argument("--revision", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-candidates", type=int, default=24)
    args = parser.parse_args(argv)

    try:
        result = run(
            revision_path=args.revision,
            baseline_path=args.baseline,
            output_path=args.output,
            max_candidates=args.max_candidates,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "parameter_optimization_plan_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "optimization_state": result["optimization_state"],
        "champion_strategy": result["champion_strategy"],
        "revision_id": result["revision_id"],
        "total_search_combinations": result["total_search_combinations"],
        "selected_candidate_count": result["selected_candidate_count"],
        "requires_offline_backtest": result["requires_offline_backtest"],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "parameter_optimization_report_sha256": result[
            "parameter_optimization_report_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
