from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "72.0"
SCHEMA_VERSION = "v72.0.strategy_revision_requalification.1"
SUPPORTED_WALK_FORWARD_SCHEMA = "v70.0.walk_forward_validation.1"


class RevisionAnalysisError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RevisionAnalysisError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RevisionAnalysisError(f"invalid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise RevisionAnalysisError("top-level JSON must be an object")
    return data


def validate_walk_forward(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise RevisionAnalysisError("walk-forward status must be PASS")
    if report.get("schema_version") != SUPPORTED_WALK_FORWARD_SCHEMA:
        raise RevisionAnalysisError("unsupported walk-forward schema_version")
    if report.get("network_used") is not False:
        raise RevisionAnalysisError("walk-forward network_used must be false")
    if report.get("approved_for_live") is not False:
        raise RevisionAnalysisError("walk-forward approved_for_live must be false")

    windows = report.get("windows")
    if not isinstance(windows, list) or not windows:
        raise RevisionAnalysisError("windows must be a non-empty list")

    if report.get("window_count") != len(windows):
        raise RevisionAnalysisError("window_count mismatch")


def num(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RevisionAnalysisError(f"{field} must be numeric") from exc


def analyze_window(window: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(window, dict):
        raise RevisionAnalysisError("window entry must be an object")

    train = window.get("train_metrics")
    forward = window.get("forward_metrics")
    if not isinstance(train, dict) or not isinstance(forward, dict):
        raise RevisionAnalysisError("window metrics must be objects")

    reasons: List[str] = []

    forward_win_rate = num(forward.get("win_rate"), "forward win_rate")
    forward_profit_factor = num(forward.get("profit_factor"), "forward profit_factor")
    forward_expectancy = num(forward.get("expectancy"), "forward expectancy")
    retention = num(window.get("expectancy_retention"), "expectancy_retention")

    if forward_win_rate < 0.45:
        reasons.append("LOW_WIN_RATE")
    if forward_profit_factor < 1.0:
        reasons.append("LOW_PROFIT_FACTOR")
    if forward_expectancy <= 0:
        reasons.append("NON_POSITIVE_EXPECTANCY")
    if retention < 0.25:
        reasons.append("LOW_EXPECTANCY_RETENTION")

    reported_status = str(window.get("window_status", "")).upper()
    derived_status = "PASS" if not reasons else "FAIL"

    if reported_status not in {"PASS", "FAIL"}:
        raise RevisionAnalysisError("window_status must be PASS or FAIL")
    if reported_status != derived_status:
        raise RevisionAnalysisError(
            f"window status mismatch for window {window.get('window')}"
        )

    if len(reasons) >= 3:
        severity = "CRITICAL"
    elif len(reasons) == 2:
        severity = "HIGH"
    elif len(reasons) == 1:
        severity = "MODERATE"
    else:
        severity = "NONE"

    return {
        "window": window.get("window"),
        "window_status": reported_status,
        "severity": severity,
        "failure_reasons": reasons,
        "metrics": {
            "train_expectancy": train.get("expectancy"),
            "forward_expectancy": forward.get("expectancy"),
            "forward_win_rate": forward.get("win_rate"),
            "forward_profit_factor": forward.get("profit_factor"),
            "expectancy_retention": window.get("expectancy_retention"),
        },
    }


def build_recommendations(reason_counts: Counter, failed_windows: int) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []

    def add(code: str, priority: str, title: str, rationale: str, actions: List[str]) -> None:
        recommendations.append({
            "code": code,
            "priority": priority,
            "title": title,
            "rationale": rationale,
            "actions": actions,
        })

    if reason_counts["LOW_WIN_RATE"]:
        add(
            "REV-ENTRY-QUALITY",
            "HIGH",
            "Strengthen entry-quality filters",
            "Forward win rate was below the required threshold in "
            f"{reason_counts['LOW_WIN_RATE']} failed window(s).",
            [
                "Require stronger signal confirmation before entry",
                "Add trend-alignment and minimum-volume filters",
                "Reject entries during weak or conflicting market conditions",
            ],
        )

    if reason_counts["LOW_PROFIT_FACTOR"]:
        add(
            "REV-LOSS-CONTROL",
            "HIGH",
            "Improve loss containment",
            "Forward profit factor fell below 1.0 in "
            f"{reason_counts['LOW_PROFIT_FACTOR']} failed window(s).",
            [
                "Tighten invalidation and stop-loss rules",
                "Cap repeated losses in the same symbol or market regime",
                "Review risk-reward requirements before order approval",
            ],
        )

    if reason_counts["NON_POSITIVE_EXPECTANCY"]:
        add(
            "REV-EDGE-RECOVERY",
            "CRITICAL",
            "Restore positive forward expectancy",
            "The strategy produced non-positive forward expectancy in "
            f"{reason_counts['NON_POSITIVE_EXPECTANCY']} failed window(s).",
            [
                "Remove low-quality setup variants",
                "Re-estimate reward-to-risk assumptions",
                "Separate profitable and unprofitable signal subtypes",
            ],
        )

    if reason_counts["LOW_EXPECTANCY_RETENTION"]:
        add(
            "REV-ROBUSTNESS",
            "HIGH",
            "Reduce overfitting and improve robustness",
            "Forward expectancy retained less than 25% of train expectancy in "
            f"{reason_counts['LOW_EXPECTANCY_RETENTION']} failed window(s).",
            [
                "Reduce parameter complexity",
                "Prefer broad stable parameter ranges over narrow optima",
                "Add regime-aware validation before strategy promotion",
            ],
        )

    if failed_windows:
        add(
            "REV-REQUALIFICATION",
            "MANDATORY",
            "Run full requalification after revision",
            f"{failed_windows} walk-forward window(s) failed.",
            [
                "Generate a new revision identifier",
                "Rebuild paper scenarios for all candidate strategies",
                "Rerun V68 analytics, V69 tournament, V70 walk-forward, and V71 gate",
            ],
        )

    priority_order = {"CRITICAL": 0, "MANDATORY": 1, "HIGH": 2, "MODERATE": 3, "LOW": 4}
    recommendations.sort(key=lambda item: (priority_order[item["priority"]], item["code"]))
    for index, item in enumerate(recommendations, start=1):
        item["rank"] = index

    return recommendations


def build_revision_report(
    walk_forward: Dict[str, Any],
    revision_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_walk_forward(walk_forward)

    analyses = [analyze_window(w) for w in walk_forward["windows"]]
    failed = [w for w in analyses if w["window_status"] == "FAIL"]
    passed = [w for w in analyses if w["window_status"] == "PASS"]

    reason_counts: Counter = Counter()
    severity_counts: Counter = Counter()
    for item in failed:
        reason_counts.update(item["failure_reasons"])
        severity_counts.update([item["severity"]])

    failed_count = len(failed)
    denominator = failed_count if failed_count else 1

    failure_distribution = {
        reason: {
            "count": count,
            "failed_window_rate": f"{count / denominator:.6f}",
        }
        for reason, count in sorted(reason_counts.items())
    }

    recommendations = build_recommendations(reason_counts, failed_count)

    if failed_count:
        requalification_state = "REVISION_REQUIRED"
        decision = "strategy_revision_required"
        requires_requalification = True
    else:
        requalification_state = "NO_REVISION_REQUIRED"
        decision = "strategy_revision_not_required"
        requires_requalification = False

    if revision_id is None:
        revision_id = f"REV-{walk_forward.get('champion_strategy', 'strategy')}-V72"
    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    report = {
        "status": "PASS",
        "decision": decision,
        "requalification_state": requalification_state,
        "revision_id": revision_id,
        "created_at": created_at,
        "parent_version": walk_forward.get("version"),
        "champion_strategy": walk_forward.get("champion_strategy"),
        "source_validation_state": walk_forward.get("validation_state"),
        "source_window_count": walk_forward.get("window_count"),
        "pass_window_count": len(passed),
        "fail_window_count": failed_count,
        "source_pass_rate": walk_forward.get("pass_rate"),
        "failed_windows": failed,
        "passed_windows": passed,
        "failure_distribution": failure_distribution,
        "severity_distribution": dict(sorted(severity_counts.items())),
        "recommendations": recommendations,
        "revision_plan": {
            "required": requires_requalification,
            "next_version": "72.1",
            "pipeline": [
                "strategy_revision",
                "paper_scenario_regeneration",
                "v68_analytics",
                "v69_strategy_tournament",
                "v70_walk_forward_validation",
                "v71_monte_carlo_gate",
            ],
            "promotion_rule": (
                "Do not progress to Monte Carlo unless V70 returns APPROVED "
                "and requires_monte_carlo_validation=true."
            ),
        },
        "requires_strategy_revision": requires_requalification,
        "requires_requalification": requires_requalification,
        "approved_for_live": False,
        "network_used": False,
        "source_walk_forward_report_sha256": walk_forward.get(
            "walk_forward_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }

    report["analysis_sha256"] = sha256_of({
        "failed_windows": report["failed_windows"],
        "failure_distribution": report["failure_distribution"],
        "severity_distribution": report["severity_distribution"],
    })
    report["recommendation_sha256"] = sha256_of(report["recommendations"])
    report["strategy_revision_report_sha256"] = sha256_of(report)
    return report


def run(
    input_path: Path,
    output_path: Path,
    revision_id: Optional[str] = None,
) -> Dict[str, Any]:
    source = read_json(input_path)
    result = build_revision_report(source, revision_id=revision_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V72 Strategy Revision & Requalification Engine"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--revision-id")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        result = run(
            input_path=args.input,
            output_path=args.output,
            revision_id=args.revision_id,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "strategy_revision_analysis_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    summary = {
        "status": result["status"],
        "decision": result["decision"],
        "requalification_state": result["requalification_state"],
        "revision_id": result["revision_id"],
        "champion_strategy": result["champion_strategy"],
        "pass_window_count": result["pass_window_count"],
        "fail_window_count": result["fail_window_count"],
        "requires_strategy_revision": result["requires_strategy_revision"],
        "requires_requalification": result["requires_requalification"],
        "recommendation_count": len(result["recommendations"]),
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "strategy_revision_report_sha256": result[
            "strategy_revision_report_sha256"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
