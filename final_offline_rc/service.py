from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile
from typing import Any

from .audit import (
    CredentialLeakageAudit,
    GitAudit,
    JsonIntegrityAudit,
    ManifestInventory,
    ReleaseInventory,
    RepositoryStructureAudit,
    RequiredStageAudit,
    SafetyInvariantAudit,
    sha256_file,
)


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/final_offline_release_candidate/actual"
    actual.mkdir(parents=True, exist_ok=True)

    required_stages = RequiredStageAudit().run(root)
    json_integrity = JsonIntegrityAudit().run(root)
    manifests = ManifestInventory().run(root)
    safety = SafetyInvariantAudit().run(root)
    credentials = CredentialLeakageAudit().run(root)
    structure = RepositoryStructureAudit().run(root)
    git = GitAudit().run(root)

    inventory = ReleaseInventory().build(
        root=root,
        output=actual / "release_inventory.json",
        include_paths=[
            "deployment",
            "alpaca_paper_read",
            "p2_broker_read",
            "reporting_notification",
            "multi_broker_plugins",
            "feature_optimization",
            "shadow_production",
            "ai_monitoring_runtime",
            "operational_resilience",
            "secure_control_plane",
            "runtime_deployment",
            "tools",
            "release",
        ],
    )

    checks = {
        "all_required_stages_pass": (
            required_stages["all_required_stages_pass"] is True
        ),
        "json_integrity_pass": json_integrity["status"] == "PASS",
        "manifests_valid": manifests["all_valid"] is True,
        "safety_invariants_pass": safety["status"] == "PASS",
        "credential_scan_pass": credentials["status"] == "PASS",
        "repository_structure_pass": structure["status"] == "PASS",
        "git_commands_valid": git["git_commands_valid"] is True,
        "main_branch": git["branch_main"] is True,
        "inventory_created": inventory["file_count"] > 0,
    }
    failed = [key for key, value in checks.items() if not value]
    passed = not failed

    result = {
        "stage": "FINAL_OFFLINE_RELEASE_CANDIDATE_AUDIT",
        "state": (
            "OFFLINE_RELEASE_CANDIDATE_READY"
            if passed else "OFFLINE_RELEASE_CANDIDATE_BLOCKED"
        ),
        "status": "PASS" if passed else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failed": failed,
        "warnings": (
            ["WORKING_TREE_NOT_CLEAN"]
            if not git["working_tree_clean"] else []
        ),
        "required_stage_audit": required_stages,
        "json_integrity_audit": json_integrity,
        "manifest_inventory": manifests,
        "safety_invariant_audit": safety,
        "credential_leakage_audit": credentials,
        "repository_structure_audit": structure,
        "git_audit": git,
        "release_inventory": inventory,
        "p3_actual_paper_order_validation_completed": False,
        "p3_actual_paper_order_validation_required": True,
        "offline_release_candidate_ready": passed,
        "production_release_allowed": False,
        "live_release_allowed": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "actual_runtime_started": False,
        "actual_service_installed": False,
        "actual_release_applied": False,
        "next_market_dependent_action": (
            "P3_ACTUAL_PAPER_ORDER_VALIDATION"
        ),
    }

    result_path = actual / "final_offline_rc_audit_result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    certificate = {
        "certificate_stage": "FINAL_OFFLINE_RELEASE_CANDIDATE",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "eligible": passed,
        "status": "PASS" if passed else "BLOCKED",
        "offline_release_candidate_ready": passed,
        "p3_actual_paper_order_validation_completed": False,
        "production_release_allowed": False,
        "live_release_allowed": False,
        "working_tree_clean": git["working_tree_clean"],
        "working_tree_change_count": git["working_tree_change_count"],
        "source_branch": git["branch"],
        "source_commit": git["commit"],
        "audit_result_sha256": sha256_file(result_path),
        "release_inventory_sha256": inventory["inventory_sha256"],
        "failed": failed,
        "warnings": result["warnings"],
    }
    certificate_path = actual / "final_offline_rc_certificate.json"
    certificate_path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    bundle_path = actual / "final_offline_release_candidate.zip"
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in [
            result_path,
            certificate_path,
            actual / "release_inventory.json",
        ]:
            archive.write(path, path.name)

        for path in root.glob("*MANIFEST*.json"):
            archive.write(path, f"manifests/{path.name}")

        docs = (
            root / "release/final_offline_release_candidate/docs/"
                   "FINAL_OFFLINE_RELEASE_CANDIDATE.md"
        )
        if docs.exists():
            archive.write(docs, f"docs/{docs.name}")

    bundle = {
        "bundle_path": str(bundle_path.relative_to(root)),
        "bundle_size_bytes": bundle_path.stat().st_size,
        "bundle_sha256": sha256_file(bundle_path),
        "actual_release_applied": False,
    }
    (actual / "final_offline_rc_bundle.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return result
