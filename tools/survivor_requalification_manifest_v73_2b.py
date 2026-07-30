from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "73.2B"
SCHEMA_VERSION = "v73.2b.survivor_requalification_manifest.1"
SUPPORTED_V732A_SCHEMA = "v73.2a.offline_candidate_quality_gate.1"


class ManifestError(ValueError):
    pass


DEFAULT_MAX_SURVIVORS = 5


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ManifestError("top-level JSON must be an object")
    return data


def validate_quality_gate(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise ManifestError("V73.2A status must be PASS")
    if report.get("schema_version") != SUPPORTED_V732A_SCHEMA:
        raise ManifestError("unsupported V73.2A schema_version")
    if report.get("quality_gate_state") != "SURVIVORS_AVAILABLE":
        raise ManifestError("quality_gate_state must be SURVIVORS_AVAILABLE")
    if report.get("network_used") is not False:
        raise ManifestError("network_used must be false")
    if report.get("approved_for_live") is not False:
        raise ManifestError("approved_for_live must be false")
    if report.get("requires_requalification") is not True:
        raise ManifestError("requires_requalification must be true")
    evaluations = report.get("candidate_evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        raise ManifestError("candidate_evaluations must be a non-empty list")


def survivor_sort_key(item: Dict[str, Any]) -> tuple:
    return (
        int(item.get("quality_rank") or 999999),
        -float(item.get("quality_score", 0.0)),
        int(item.get("source_backtest_rank") or 999999),
        str(item.get("candidate_id", "")),
    )


def build_validation_contract(candidate: Dict[str, Any]) -> Dict[str, Any]:
    candidate_id = candidate["candidate_id"]
    parameters = candidate.get("parameters")
    if not isinstance(parameters, dict):
        raise ManifestError(f"parameters missing for {candidate_id}")

    return {
        "candidate_id": candidate_id,
        "priority": candidate["requalification_priority"],
        "parameters": parameters,
        "required_stages": [
            {
                "stage": "V68",
                "name": "analytics_revalidation",
                "required_output": (
                    f"release/v74/{candidate_id}/analytics_revalidation_v68.json"
                ),
                "required_decision": "analytics_pipeline_completed",
            },
            {
                "stage": "V70",
                "name": "walk_forward_revalidation",
                "required_output": (
                    f"release/v74/{candidate_id}/walk_forward_revalidation_v70.json"
                ),
                "required_state": "APPROVED",
            },
            {
                "stage": "V71",
                "name": "monte_carlo_revalidation",
                "required_output": (
                    f"release/v74/{candidate_id}/monte_carlo_revalidation_v71.json"
                ),
                "required_state": "APPROVED",
            },
        ],
        "promotion_rule": (
            "Candidate is eligible for provisional paper promotion only when "
            "all required stages pass. Live approval remains prohibited."
        ),
        "approved_for_live": False,
    }


def build_manifest(
    quality_gate_report: Dict[str, Any],
    max_survivors: int = DEFAULT_MAX_SURVIVORS,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_quality_gate(quality_gate_report)

    if max_survivors < 1:
        raise ManifestError("max_survivors must be at least 1")

    survivors = [
        item for item in quality_gate_report["candidate_evaluations"]
        if item.get("quality_gate_status") == "PASS"
    ]
    if not survivors:
        raise ManifestError("no PASS survivors found")

    survivors.sort(key=survivor_sort_key)
    selected = survivors[:max_survivors]

    manifest_candidates: List[Dict[str, Any]] = []
    for priority, item in enumerate(selected, start=1):
        manifest_candidates.append({
            "candidate_id": item["candidate_id"],
            "requalification_priority": priority,
            "quality_rank": item.get("quality_rank"),
            "quality_score": item.get("quality_score"),
            "source_backtest_rank": item.get("source_backtest_rank"),
            "metrics": item.get("metrics"),
            "parameters": item.get("parameters"),
            "requalification_state": "PENDING",
            "required_validations": ["V68", "V70", "V71"],
            "approved_for_live": False,
        })

    contracts = [build_validation_contract(item) for item in manifest_candidates]

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion_id = manifest_candidates[0]["candidate_id"]
    runner_up_id = (
        manifest_candidates[1]["candidate_id"]
        if len(manifest_candidates) > 1
        else None
    )

    report = {
        "status": "PASS",
        "decision": "requalification_manifest_created",
        "manifest_state": "READY_FOR_REQUALIFICATION",
        "created_at": created_at,
        "champion_strategy": quality_gate_report.get("champion_strategy"),
        "revision_id": quality_gate_report.get("revision_id"),
        "source_candidate_count": quality_gate_report.get("candidate_count"),
        "source_survivor_count": quality_gate_report.get("survivor_count"),
        "selected_survivor_count": len(manifest_candidates),
        "max_survivors": max_survivors,
        "champion_candidate_id": champion_id,
        "runner_up_candidate_id": runner_up_id,
        "selected_candidates": manifest_candidates,
        "validation_contracts": contracts,
        "execution_order": [item["candidate_id"] for item in manifest_candidates],
        "next_step": {
            "version": "74.0",
            "action": "execute_candidate_requalification_pipeline",
            "stages": ["V68", "V70", "V71"],
        },
        "requires_requalification_execution": True,
        "approved_for_live": False,
        "network_used": False,
        "source_v73_2a_report_sha256": quality_gate_report.get(
            "quality_gate_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }

    report["selected_candidates_sha256"] = sha256_of(
        report["selected_candidates"]
    )
    report["validation_contracts_sha256"] = sha256_of(
        report["validation_contracts"]
    )
    report["requalification_manifest_sha256"] = sha256_of(report)
    return report


def run(
    input_path: Path,
    output_path: Path,
    max_survivors: int,
) -> Dict[str, Any]:
    quality_gate_report = read_json(input_path)
    result = build_manifest(
        quality_gate_report,
        max_survivors=max_survivors,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V73.2B Survivor Requalification Manifest"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--max-survivors",
        type=int,
        default=DEFAULT_MAX_SURVIVORS,
    )
    args = parser.parse_args(argv)

    try:
        result = run(
            input_path=args.input,
            output_path=args.output,
            max_survivors=args.max_survivors,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "requalification_manifest_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "manifest_state": result["manifest_state"],
        "selected_survivor_count": result["selected_survivor_count"],
        "champion_candidate_id": result["champion_candidate_id"],
        "runner_up_candidate_id": result["runner_up_candidate_id"],
        "requires_requalification_execution": result[
            "requires_requalification_execution"
        ],
        "approved_for_live": result["approved_for_live"],
        "network_used": result["network_used"],
        "requalification_manifest_sha256": result[
            "requalification_manifest_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
