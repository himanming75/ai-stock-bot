from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "75.1A"
SCHEMA_VERSION = "v75.1a.champion_promotion_package.1"
SUPPORTED_SOURCE_SCHEMA = "v74.candidate_requalification_pipeline.1"


class PromotionPackageError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromotionPackageError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromotionPackageError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PromotionPackageError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise PromotionPackageError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PromotionPackageError("unsupported source schema_version")
    if source.get("pipeline_state") != "APPROVED_SURVIVORS_AVAILABLE":
        raise PromotionPackageError(
            "pipeline_state must be APPROVED_SURVIVORS_AVAILABLE"
        )
    if source.get("approved_for_live") is not False:
        raise PromotionPackageError("source approved_for_live must be false")
    if source.get("network_used") is not False:
        raise PromotionPackageError("source network_used must be false")

    approved_count = int(source.get("approved_candidate_count", 0))
    approved_ids = source.get("approved_candidate_ids")
    results = source.get("execution_results")
    if approved_count < 1:
        raise PromotionPackageError("approved_candidate_count must be at least 1")
    if not isinstance(approved_ids, list) or not approved_ids:
        raise PromotionPackageError("approved_candidate_ids must be non-empty")
    if not isinstance(results, list) or not results:
        raise PromotionPackageError("execution_results must be non-empty")

    champion_id = source.get("champion_candidate_id")
    if not champion_id:
        raise PromotionPackageError("champion_candidate_id is required")
    if champion_id not in approved_ids:
        raise PromotionPackageError("champion must be in approved_candidate_ids")

    runner_up_id = source.get("runner_up_candidate_id")
    if runner_up_id is not None and runner_up_id not in approved_ids:
        raise PromotionPackageError("runner-up must be in approved_candidate_ids")
    if runner_up_id == champion_id:
        raise PromotionPackageError("runner-up must differ from champion")


def approved_result_map(source: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result_map: Dict[str, Dict[str, Any]] = {}
    for result in source["execution_results"]:
        candidate_id = result.get("candidate_id")
        if not candidate_id:
            raise PromotionPackageError("execution result candidate_id missing")
        if candidate_id in result_map:
            raise PromotionPackageError(f"duplicate candidate_id: {candidate_id}")
        result_map[candidate_id] = result
    return result_map


def validate_selected_candidate(
    candidate_id: str,
    result: Dict[str, Any],
    role: str,
) -> None:
    if result.get("requalification_state") != "APPROVED":
        raise PromotionPackageError(f"{role} requalification_state must be APPROVED")
    if result.get("eligible_for_provisional_paper_promotion") is not True:
        raise PromotionPackageError(
            f"{role} must be eligible for provisional paper promotion"
        )
    if result.get("approved_for_live") is not False:
        raise PromotionPackageError(f"{role} approved_for_live must be false")
    score = result.get("requalification_score")
    if not isinstance(score, (int, float)):
        raise PromotionPackageError(f"{role} requalification_score missing")
    stages = result.get("stage_results")
    if not isinstance(stages, list) or len(stages) != 3:
        raise PromotionPackageError(f"{role} must have exactly 3 stage results")
    expected = ["V68", "V70", "V71"]
    observed = [stage.get("stage") for stage in stages]
    if observed != expected:
        raise PromotionPackageError(
            f"{role} stage sequence must be V68 -> V70 -> V71"
        )
    if any(stage.get("status") != "PASS" for stage in stages):
        raise PromotionPackageError(f"{role} all stages must PASS")


def compact_stage_evidence(stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for stage in stages:
        item = {
            "stage": stage.get("stage"),
            "name": stage.get("name"),
            "status": stage.get("status"),
        }
        for key in (
            "decision",
            "validation_state",
            "pass_rate",
            "probability_positive",
            "p05_net_pnl",
        ):
            if key in stage and stage.get(key) is not None:
                item[key] = stage.get(key)
        evidence.append(item)
    return evidence


def build_candidate_package(
    source: Dict[str, Any],
    result: Dict[str, Any],
    role: str,
    created_at: str,
) -> Dict[str, Any]:
    candidate_id = result["candidate_id"]
    package = {
        "status": "PASS",
        "decision": "provisional_paper_candidate_packaged",
        "package_role": role,
        "candidate_id": candidate_id,
        "strategy": source.get("champion_strategy"),
        "revision_id": source.get("revision_id"),
        "requalification_priority": result.get("requalification_priority"),
        "requalification_score": result.get("requalification_score"),
        "parameters": result.get("parameters"),
        "stage_evidence": compact_stage_evidence(result["stage_results"]),
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "paper_activation_state": "NOT_ACTIVATED",
        "requires_operator_review": True,
        "requires_rollback_package": True,
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": source.get(
            "candidate_requalification_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    package["candidate_package_sha256"] = sha256_of(package)
    return package


def build_promotion_package(
    source: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    result_map = approved_result_map(source)

    champion_id = source["champion_candidate_id"]
    runner_up_id = source.get("runner_up_candidate_id")

    if champion_id not in result_map:
        raise PromotionPackageError("champion missing from execution_results")
    champion_result = result_map[champion_id]
    validate_selected_candidate(champion_id, champion_result, "champion")

    runner_up_result = None
    if runner_up_id is not None:
        if runner_up_id not in result_map:
            raise PromotionPackageError("runner-up missing from execution_results")
        runner_up_result = result_map[runner_up_id]
        validate_selected_candidate(runner_up_id, runner_up_result, "runner-up")
        if float(champion_result["requalification_score"]) < float(
            runner_up_result["requalification_score"]
        ):
            raise PromotionPackageError(
                "champion score must be greater than or equal to runner-up score"
            )

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion_package = build_candidate_package(
        source, champion_result, "CHAMPION", created_at
    )
    runner_up_package = (
        build_candidate_package(source, runner_up_result, "RUNNER_UP", created_at)
        if runner_up_result is not None
        else None
    )

    summary = {
        "status": "PASS",
        "decision": "champion_promotion_package_created",
        "package_state": "READY_FOR_PROMOTION_MANIFEST",
        "champion_candidate_id": champion_id,
        "runner_up_candidate_id": runner_up_id,
        "champion_score": champion_result["requalification_score"],
        "runner_up_score": (
            runner_up_result["requalification_score"]
            if runner_up_result is not None else None
        ),
        "candidate_package_count": 2 if runner_up_package else 1,
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "requires_promotion_manifest": True,
        "requires_rollback_manifest": True,
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": source.get(
            "candidate_requalification_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    summary["promotion_summary_sha256"] = sha256_of(summary)

    package = {
        "status": "PASS",
        "decision": "champion_promotion_bundle_created",
        "package_state": "READY_FOR_PROMOTION_MANIFEST",
        "champion_package": champion_package,
        "runner_up_package": runner_up_package,
        "promotion_summary": summary,
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_v74_report_sha256": source.get(
            "candidate_requalification_report_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    package["promotion_package_sha256"] = sha256_of(package)
    return package


def write_outputs(package: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "promotion_package_v75_1a.json": package,
        "champion_package_v75_1a.json": package["champion_package"],
        "promotion_summary_v75_1a.json": package["promotion_summary"],
    }
    if package["runner_up_package"] is not None:
        files["runner_up_package_v75_1a.json"] = package["runner_up_package"]

    for filename, data in files.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "promotion_package_v75_1a.sha256").write_text(
        package["promotion_package_sha256"] + "\n",
        encoding="utf-8",
    )


def run(source_path: Path, output_dir: Path) -> Dict[str, Any]:
    source = read_json(source_path)
    package = build_promotion_package(source)
    write_outputs(package, output_dir)
    return package


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.1A Champion Promotion Package Builder"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        package = run(args.input, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "champion_promotion_package_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    summary = package["promotion_summary"]
    print(json.dumps({
        "status": package["status"],
        "decision": package["decision"],
        "package_state": package["package_state"],
        "champion_candidate_id": summary["champion_candidate_id"],
        "runner_up_candidate_id": summary["runner_up_candidate_id"],
        "champion_score": summary["champion_score"],
        "runner_up_score": summary["runner_up_score"],
        "candidate_package_count": summary["candidate_package_count"],
        "promotion_scope": summary["promotion_scope"],
        "requires_promotion_manifest": summary["requires_promotion_manifest"],
        "requires_rollback_manifest": summary["requires_rollback_manifest"],
        "approved_for_live": package["approved_for_live"],
        "network_used": package["network_used"],
        "promotion_package_sha256": package["promotion_package_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
