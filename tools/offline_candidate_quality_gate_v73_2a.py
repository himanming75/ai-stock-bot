from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "73.2A"
SCHEMA_VERSION = "v73.2a.offline_candidate_quality_gate.1"
SUPPORTED_V731_SCHEMA = "v73.1.offline_candidate_backtest.1"


class QualityGateError(ValueError):
    pass


DEFAULT_THRESHOLDS = {
    "minimum_trade_count": 5,
    "minimum_win_rate": 0.45,
    "minimum_profit_factor": 1.10,
    "minimum_expectancy": 0.0,
    "minimum_net_pnl": 0.0,
}


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QualityGateError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QualityGateError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise QualityGateError("top-level JSON must be an object")
    return data


def validate_report(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise QualityGateError("V73.1 status must be PASS")
    if report.get("schema_version") != SUPPORTED_V731_SCHEMA:
        raise QualityGateError("unsupported V73.1 schema_version")
    if report.get("execution_state") != "BACKTESTS_COMPLETED":
        raise QualityGateError("execution_state must be BACKTESTS_COMPLETED")
    if report.get("network_used") is not False:
        raise QualityGateError("network_used must be false")
    if report.get("approved_for_live") is not False:
        raise QualityGateError("approved_for_live must be false")
    results = report.get("candidate_results")
    if not isinstance(results, list) or not results:
        raise QualityGateError("candidate_results must be a non-empty list")


def validate_thresholds(thresholds: Dict[str, Any]) -> None:
    required = set(DEFAULT_THRESHOLDS)
    if not required.issubset(thresholds):
        missing = sorted(required - set(thresholds))
        raise QualityGateError(f"missing thresholds: {', '.join(missing)}")

    if int(thresholds["minimum_trade_count"]) < 1:
        raise QualityGateError("minimum_trade_count must be at least 1")
    for key in ["minimum_win_rate", "minimum_profit_factor"]:
        if float(thresholds[key]) < 0:
            raise QualityGateError(f"{key} must be non-negative")


def quality_reasons(
    metrics: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> List[str]:
    reasons: List[str] = []

    if int(metrics.get("trade_count", 0)) < int(thresholds["minimum_trade_count"]):
        reasons.append("INSUFFICIENT_TRADE_COUNT")

    if float(metrics.get("win_rate", 0.0)) < float(thresholds["minimum_win_rate"]):
        reasons.append("LOW_WIN_RATE")

    pf = metrics.get("profit_factor")
    if pf is None:
        pass
    elif float(pf) < float(thresholds["minimum_profit_factor"]):
        reasons.append("LOW_PROFIT_FACTOR")

    if float(metrics.get("expectancy", 0.0)) <= float(thresholds["minimum_expectancy"]):
        reasons.append("NON_POSITIVE_EXPECTANCY")

    if float(metrics.get("net_pnl", 0.0)) <= float(thresholds["minimum_net_pnl"]):
        reasons.append("NON_POSITIVE_NET_PNL")

    return reasons


def score_candidate(
    metrics: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> float:
    trade_count = int(metrics.get("trade_count", 0))
    win_rate = float(metrics.get("win_rate", 0.0))
    expectancy = float(metrics.get("expectancy", 0.0))
    net_pnl = float(metrics.get("net_pnl", 0.0))
    pf = metrics.get("profit_factor")
    pf_score = 5.0 if pf is None else min(float(pf), 5.0)

    score = (
        min(trade_count, 50) * 0.5
        + win_rate * 40
        + pf_score * 8
        + max(expectancy, 0.0) * 0.05
        + max(net_pnl, 0.0) * 0.005
    )
    return round(score, 6)


def evaluate_candidate(
    candidate_result: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_id = candidate_result.get("candidate_id")
    metrics = candidate_result.get("metrics")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise QualityGateError("candidate_id is required")
    if not isinstance(metrics, dict):
        raise QualityGateError(f"metrics missing for {candidate_id}")

    reasons = quality_reasons(metrics, thresholds)
    status = "PASS" if not reasons else "FAIL"

    return {
        "candidate_id": candidate_id,
        "source_backtest_rank": candidate_result.get("backtest_rank"),
        "quality_gate_status": status,
        "failure_reasons": reasons,
        "quality_score": score_candidate(metrics, thresholds),
        "metrics": metrics,
        "parameters": candidate_result.get("parameters"),
        "approved_for_live": False,
    }


def ranking_key(item: Dict[str, Any]) -> tuple:
    return (
        0 if item["quality_gate_status"] == "PASS" else 1,
        -float(item["quality_score"]),
        int(item.get("source_backtest_rank") or 999999),
        item["candidate_id"],
    )


def build_quality_gate_report(
    backtest_report: Dict[str, Any],
    thresholds: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_report(backtest_report)

    if thresholds is None:
        thresholds = dict(DEFAULT_THRESHOLDS)
    else:
        merged = dict(DEFAULT_THRESHOLDS)
        merged.update(thresholds)
        thresholds = merged

    validate_thresholds(thresholds)

    evaluations = [
        evaluate_candidate(candidate, thresholds)
        for candidate in backtest_report["candidate_results"]
    ]
    evaluations.sort(key=ranking_key)

    for rank, item in enumerate(evaluations, start=1):
        item["quality_rank"] = rank

    survivors = [
        item for item in evaluations
        if item["quality_gate_status"] == "PASS"
    ]
    failures = [
        item for item in evaluations
        if item["quality_gate_status"] == "FAIL"
    ]

    failure_distribution: Dict[str, int] = {}
    for item in failures:
        for reason in item["failure_reasons"]:
            failure_distribution[reason] = failure_distribution.get(reason, 0) + 1

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    decision = (
        "quality_gate_survivors_available"
        if survivors
        else "quality_gate_no_survivors"
    )

    report = {
        "status": "PASS",
        "decision": decision,
        "quality_gate_state": (
            "SURVIVORS_AVAILABLE" if survivors else "NO_SURVIVORS"
        ),
        "created_at": created_at,
        "champion_strategy": backtest_report.get("champion_strategy"),
        "revision_id": backtest_report.get("revision_id"),
        "thresholds": thresholds,
        "candidate_count": len(evaluations),
        "survivor_count": len(survivors),
        "failed_count": len(failures),
        "failure_distribution": dict(sorted(failure_distribution.items())),
        "candidate_evaluations": evaluations,
        "survivor_candidate_ids": [
            item["candidate_id"] for item in survivors
        ],
        "provisional_champion_candidate_id": (
            survivors[0]["candidate_id"] if survivors else None
        ),
        "next_step": {
            "version": "73.2B",
            "action": "select_survivors_and_build_requalification_manifest",
            "required_validations": [
                "v68_analytics",
                "v70_walk_forward",
                "v71_monte_carlo",
            ],
        },
        "requires_requalification": bool(survivors),
        "approved_for_live": False,
        "network_used": False,
        "source_v73_1_report_sha256": backtest_report.get(
            "offline_candidate_backtest_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }

    report["candidate_evaluations_sha256"] = sha256_of(
        report["candidate_evaluations"]
    )
    report["quality_gate_report_sha256"] = sha256_of(report)
    return report


def run(
    input_path: Path,
    output_path: Path,
    thresholds_path: Optional[Path] = None,
) -> Dict[str, Any]:
    report = read_json(input_path)
    thresholds = read_json(thresholds_path) if thresholds_path else None
    result = build_quality_gate_report(report, thresholds=thresholds)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V73.2A Offline Candidate Quality Gate"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--thresholds", type=Path)
    args = parser.parse_args(argv)

    try:
        result = run(
            input_path=args.input,
            output_path=args.output,
            thresholds_path=args.thresholds,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "quality_gate_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "quality_gate_state": result["quality_gate_state"],
        "candidate_count": result["candidate_count"],
        "survivor_count": result["survivor_count"],
        "failed_count": result["failed_count"],
        "provisional_champion_candidate_id": result[
            "provisional_champion_candidate_id"
        ],
        "requires_requalification": result["requires_requalification"],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "quality_gate_report_sha256": result["quality_gate_report_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
