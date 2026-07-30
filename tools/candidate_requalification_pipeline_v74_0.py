from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


VERSION = "74.0"
SCHEMA_VERSION = "v74.candidate_requalification_pipeline.1"
SUPPORTED_MANIFEST_SCHEMA = "v73.2b.survivor_requalification_manifest.1"
SUPPORTED_BACKTEST_SCHEMA = "v73.1.offline_candidate_backtest.1"


class RequalificationError(ValueError):
    pass


DEFAULT_CONFIG = {
    "analytics": {
        "minimum_trade_count": 5,
        "minimum_win_rate": 0.45,
        "minimum_profit_factor": 1.10,
        "minimum_expectancy": 0.0,
        "minimum_net_pnl": 0.0,
    },
    "walk_forward": {
        "window_count": 2,
        "minimum_window_trade_count": 2,
        "minimum_pass_rate": 0.50,
        "minimum_aggregate_expectancy": 0.0,
    },
    "monte_carlo": {
        "simulation_count": 500,
        "minimum_probability_positive": 0.60,
        "minimum_p05_net_pnl": 0.0,
    },
}


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RequalificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RequalificationError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise RequalificationError("top-level JSON must be an object")
    return data


def validate_manifest(manifest: Dict[str, Any]) -> None:
    if manifest.get("status") != "PASS":
        raise RequalificationError("manifest status must be PASS")
    if manifest.get("schema_version") != SUPPORTED_MANIFEST_SCHEMA:
        raise RequalificationError("unsupported manifest schema_version")
    if manifest.get("manifest_state") != "READY_FOR_REQUALIFICATION":
        raise RequalificationError(
            "manifest_state must be READY_FOR_REQUALIFICATION"
        )
    if manifest.get("network_used") is not False:
        raise RequalificationError("manifest network_used must be false")
    if manifest.get("approved_for_live") is not False:
        raise RequalificationError("manifest approved_for_live must be false")
    candidates = manifest.get("selected_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RequalificationError("selected_candidates must be non-empty")


def validate_backtest(backtest: Dict[str, Any]) -> None:
    if backtest.get("status") != "PASS":
        raise RequalificationError("backtest status must be PASS")
    if backtest.get("schema_version") != SUPPORTED_BACKTEST_SCHEMA:
        raise RequalificationError("unsupported backtest schema_version")
    if backtest.get("execution_state") != "BACKTESTS_COMPLETED":
        raise RequalificationError("backtest execution_state invalid")
    if backtest.get("network_used") is not False:
        raise RequalificationError("backtest network_used must be false")
    if backtest.get("approved_for_live") is not False:
        raise RequalificationError("backtest approved_for_live must be false")
    results = backtest.get("candidate_results")
    if not isinstance(results, list) or not results:
        raise RequalificationError("candidate_results must be non-empty")


def merge_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    if config:
        for section, values in config.items():
            if section not in merged or not isinstance(values, dict):
                raise RequalificationError(f"invalid config section: {section}")
            merged[section].update(values)

    if int(merged["analytics"]["minimum_trade_count"]) < 1:
        raise RequalificationError("minimum_trade_count must be at least 1")
    if int(merged["walk_forward"]["window_count"]) < 2:
        raise RequalificationError("window_count must be at least 2")
    if int(merged["walk_forward"]["minimum_window_trade_count"]) < 1:
        raise RequalificationError(
            "minimum_window_trade_count must be at least 1"
        )
    if int(merged["monte_carlo"]["simulation_count"]) < 100:
        raise RequalificationError("simulation_count must be at least 100")
    return merged


def metric_profit_factor(pnls: Sequence[float]) -> Optional[float]:
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    if gross_loss > 0:
        return gross_profit / gross_loss
    if gross_profit > 0:
        return None
    return 0.0


def metrics_from_pnls(pnls: Sequence[float]) -> Dict[str, Any]:
    count = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    losses = sum(1 for x in pnls if x < 0)
    net = sum(pnls)
    pf = metric_profit_factor(pnls)
    return {
        "trade_count": count,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": round(wins / count, 6) if count else 0.0,
        "profit_factor": round(pf, 6) if pf is not None else None,
        "expectancy": round(net / count, 6) if count else 0.0,
        "net_pnl": round(net, 6),
    }


def evaluate_analytics(
    candidate_result: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    metrics = candidate_result.get("metrics")
    if not isinstance(metrics, dict):
        raise RequalificationError("candidate metrics missing")

    reasons: List[str] = []
    if int(metrics.get("trade_count", 0)) < int(config["minimum_trade_count"]):
        reasons.append("INSUFFICIENT_TRADE_COUNT")
    if float(metrics.get("win_rate", 0.0)) < float(config["minimum_win_rate"]):
        reasons.append("LOW_WIN_RATE")
    pf = metrics.get("profit_factor")
    if pf is not None and float(pf) < float(config["minimum_profit_factor"]):
        reasons.append("LOW_PROFIT_FACTOR")
    if float(metrics.get("expectancy", 0.0)) <= float(config["minimum_expectancy"]):
        reasons.append("NON_POSITIVE_EXPECTANCY")
    if float(metrics.get("net_pnl", 0.0)) <= float(config["minimum_net_pnl"]):
        reasons.append("NON_POSITIVE_NET_PNL")

    return {
        "stage": "V68",
        "name": "analytics_revalidation",
        "status": "PASS" if not reasons else "FAIL",
        "decision": (
            "analytics_pipeline_completed"
            if not reasons else "analytics_revalidation_rejected"
        ),
        "failure_reasons": reasons,
        "metrics": metrics,
    }


def split_windows(items: Sequence[float], window_count: int) -> List[List[float]]:
    windows: List[List[float]] = []
    n = len(items)
    for i in range(window_count):
        start = (i * n) // window_count
        end = ((i + 1) * n) // window_count
        windows.append(list(items[start:end]))
    return windows


def evaluate_walk_forward(
    pnls: Sequence[float],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    window_count = int(config["window_count"])
    minimum_window_trade_count = int(config["minimum_window_trade_count"])
    windows = split_windows(pnls, window_count)

    window_results: List[Dict[str, Any]] = []
    pass_count = 0
    for index, window in enumerate(windows, start=1):
        metrics = metrics_from_pnls(window)
        passed = (
            metrics["trade_count"] >= minimum_window_trade_count
            and metrics["expectancy"] > 0
            and metrics["net_pnl"] > 0
        )
        if passed:
            pass_count += 1
        window_results.append({
            "window": index,
            "status": "PASS" if passed else "FAIL",
            "metrics": metrics,
        })

    pass_rate = pass_count / window_count
    aggregate = metrics_from_pnls(pnls)
    reasons: List[str] = []
    if pass_rate < float(config["minimum_pass_rate"]):
        reasons.append("LOW_WINDOW_PASS_RATE")
    if aggregate["expectancy"] <= float(
        config["minimum_aggregate_expectancy"]
    ):
        reasons.append("NON_POSITIVE_AGGREGATE_EXPECTANCY")

    passed = not reasons
    return {
        "stage": "V70",
        "name": "walk_forward_revalidation",
        "status": "PASS" if passed else "FAIL",
        "validation_state": "APPROVED" if passed else "REJECTED",
        "window_count": window_count,
        "pass_count": pass_count,
        "fail_count": window_count - pass_count,
        "pass_rate": round(pass_rate, 6),
        "aggregate_metrics": aggregate,
        "window_results": window_results,
        "failure_reasons": reasons,
    }


def percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        return 0.0
    index = (len(sorted_values) - 1) * probability
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return float(sorted_values[low])
    weight = index - low
    return (
        float(sorted_values[low]) * (1.0 - weight)
        + float(sorted_values[high]) * weight
    )


def deterministic_seed(candidate_id: str) -> int:
    return int(hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16], 16)


def evaluate_monte_carlo(
    candidate_id: str,
    pnls: Sequence[float],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    simulations = int(config["simulation_count"])
    if not pnls:
        return {
            "stage": "V71",
            "name": "monte_carlo_revalidation",
            "status": "FAIL",
            "validation_state": "REJECTED",
            "simulation_count": 0,
            "failure_reasons": ["NO_TRADES"],
        }

    rng = random.Random(deterministic_seed(candidate_id))
    outcomes: List[float] = []
    n = len(pnls)
    for _ in range(simulations):
        outcomes.append(sum(rng.choice(pnls) for _ in range(n)))

    outcomes.sort()
    positive_probability = sum(1 for value in outcomes if value > 0) / simulations
    p05 = percentile(outcomes, 0.05)
    median = percentile(outcomes, 0.50)
    reasons: List[str] = []

    if positive_probability < float(config["minimum_probability_positive"]):
        reasons.append("LOW_PROBABILITY_POSITIVE")
    if p05 <= float(config["minimum_p05_net_pnl"]):
        reasons.append("NON_POSITIVE_P05_NET_PNL")

    passed = not reasons
    return {
        "stage": "V71",
        "name": "monte_carlo_revalidation",
        "status": "PASS" if passed else "FAIL",
        "validation_state": "APPROVED" if passed else "REJECTED",
        "simulation_count": simulations,
        "probability_positive": round(positive_probability, 6),
        "p05_net_pnl": round(p05, 6),
        "median_net_pnl": round(median, 6),
        "failure_reasons": reasons,
        "seed": deterministic_seed(candidate_id),
    }


def candidate_score(
    analytics: Dict[str, Any],
    walk_forward: Dict[str, Any],
    monte_carlo: Dict[str, Any],
) -> float:
    metrics = analytics["metrics"]
    return round(
        float(metrics.get("expectancy", 0.0)) * 0.20
        + float(metrics.get("win_rate", 0.0)) * 25
        + float(walk_forward.get("pass_rate", 0.0)) * 25
        + float(monte_carlo.get("probability_positive", 0.0)) * 25
        + max(float(monte_carlo.get("p05_net_pnl", 0.0)), 0.0) * 0.01,
        6,
    )


def execute_candidate(
    manifest_candidate: Dict[str, Any],
    backtest_candidate: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_id = manifest_candidate["candidate_id"]
    trades = backtest_candidate.get("trades")
    if not isinstance(trades, list):
        raise RequalificationError(f"trades missing for {candidate_id}")
    pnls = [float(trade["pnl"]) for trade in trades]

    analytics = evaluate_analytics(
        backtest_candidate,
        config["analytics"],
    )

    if analytics["status"] == "PASS":
        walk_forward = evaluate_walk_forward(
            pnls,
            config["walk_forward"],
        )
    else:
        walk_forward = {
            "stage": "V70",
            "name": "walk_forward_revalidation",
            "status": "BLOCKED",
            "validation_state": "BLOCKED",
            "failure_reasons": ["V68_FAILED"],
        }

    if walk_forward["status"] == "PASS":
        monte_carlo = evaluate_monte_carlo(
            candidate_id,
            pnls,
            config["monte_carlo"],
        )
    else:
        monte_carlo = {
            "stage": "V71",
            "name": "monte_carlo_revalidation",
            "status": "BLOCKED",
            "validation_state": "BLOCKED",
            "simulation_count": 0,
            "failure_reasons": ["V70_FAILED"],
        }

    stages = [analytics, walk_forward, monte_carlo]
    passed = all(stage["status"] == "PASS" for stage in stages)

    return {
        "candidate_id": candidate_id,
        "requalification_priority": manifest_candidate.get(
            "requalification_priority"
        ),
        "parameters": manifest_candidate.get("parameters"),
        "requalification_state": "APPROVED" if passed else "REJECTED",
        "stage_results": stages,
        "requalification_score": (
            candidate_score(analytics, walk_forward, monte_carlo)
            if passed else 0.0
        ),
        "eligible_for_provisional_paper_promotion": passed,
        "approved_for_live": False,
    }


def build_pipeline_report(
    manifest: Dict[str, Any],
    backtest: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_manifest(manifest)
    validate_backtest(backtest)
    effective_config = merge_config(config)

    backtest_map = {
        item["candidate_id"]: item for item in backtest["candidate_results"]
    }

    results: List[Dict[str, Any]] = []
    for candidate in manifest["selected_candidates"]:
        candidate_id = candidate.get("candidate_id")
        if candidate_id not in backtest_map:
            raise RequalificationError(
                f"candidate missing from backtest report: {candidate_id}"
            )
        results.append(
            execute_candidate(
                candidate,
                backtest_map[candidate_id],
                effective_config,
            )
        )

    approved = [
        item for item in results
        if item["requalification_state"] == "APPROVED"
    ]
    approved.sort(
        key=lambda item: (
            -float(item["requalification_score"]),
            int(item.get("requalification_priority") or 999999),
            item["candidate_id"],
        )
    )

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion_id = approved[0]["candidate_id"] if approved else None
    runner_up_id = approved[1]["candidate_id"] if len(approved) > 1 else None

    report = {
        "status": "PASS",
        "decision": (
            "candidate_requalification_completed"
            if approved
            else "candidate_requalification_no_approved_survivors"
        ),
        "pipeline_state": (
            "APPROVED_SURVIVORS_AVAILABLE"
            if approved else "NO_APPROVED_SURVIVORS"
        ),
        "created_at": created_at,
        "champion_strategy": manifest.get("champion_strategy"),
        "revision_id": manifest.get("revision_id"),
        "selected_candidate_count": len(results),
        "approved_candidate_count": len(approved),
        "rejected_candidate_count": len(results) - len(approved),
        "champion_candidate_id": champion_id,
        "runner_up_candidate_id": runner_up_id,
        "execution_results": results,
        "approved_candidate_ids": [item["candidate_id"] for item in approved],
        "config": effective_config,
        "next_step": {
            "version": "75.0",
            "action": (
                "build_provisional_paper_promotion_package"
                if approved else "return_to_strategy_revision"
            ),
        },
        "requires_provisional_paper_review": bool(approved),
        "approved_for_live": False,
        "network_used": False,
        "source_manifest_sha256": manifest.get(
            "requalification_manifest_sha256"
        ),
        "source_backtest_sha256": backtest.get(
            "offline_candidate_backtest_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    report["execution_results_sha256"] = sha256_of(report["execution_results"])
    report["candidate_requalification_report_sha256"] = sha256_of(report)
    return report


def run(
    manifest_path: Path,
    backtest_path: Path,
    output_path: Path,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    manifest = read_json(manifest_path)
    backtest = read_json(backtest_path)
    config = read_json(config_path) if config_path else None
    result = build_pipeline_report(manifest, backtest, config=config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V74 Candidate Requalification Pipeline Executor"
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--backtest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)

    try:
        result = run(
            manifest_path=args.manifest,
            backtest_path=args.backtest,
            output_path=args.output,
            config_path=args.config,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "candidate_requalification_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "pipeline_state": result["pipeline_state"],
        "selected_candidate_count": result["selected_candidate_count"],
        "approved_candidate_count": result["approved_candidate_count"],
        "rejected_candidate_count": result["rejected_candidate_count"],
        "champion_candidate_id": result["champion_candidate_id"],
        "runner_up_candidate_id": result["runner_up_candidate_id"],
        "requires_provisional_paper_review": result[
            "requires_provisional_paper_review"
        ],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "candidate_requalification_report_sha256": result[
            "candidate_requalification_report_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
