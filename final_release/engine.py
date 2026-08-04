from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from final_release.io import load_json, write_json, append_jsonl, digest
from final_release.inventory import build_inventory
from final_release.readiness import evaluate_readiness
from final_release.certificate import build_certificate
from final_release.manifest import build_manifest
from final_release.integrity import verify_inventory
from final_release.acceptance import acceptance_test
from final_release.bundle import create_bundle
from final_release.rollback import build_rollback_manifest

def evaluate(root: Path) -> dict[str, Any]:
    policy = load_json(
        root / "release/v105_33_to_v105_64/input/"
        "final_release_policy.json"
    )
    integration = load_json(
        root / "release/v105_01_to_v105_32/actual/"
        "final_system_integration_result.json"
    )
    actual_dir = root / "release/v105_33_to_v105_64/actual"
    bundle_dir = root / "release/v105_33_to_v105_64/bundle"
    rollback_dir = root / "release/v105_33_to_v105_64/rollback"
    docs_dir = root / "release/v105_33_to_v105_64/docs"

    readiness = evaluate_readiness(integration, policy)
    certificate = build_certificate(integration, readiness, policy)
    write_json(actual_dir / "final_completion_certificate.json", certificate)

    inventory = build_inventory(root)
    write_json(actual_dir / "final_file_inventory.json", inventory)

    manifest = build_manifest(certificate, inventory, policy)
    write_json(actual_dir / "final_release_manifest.json", manifest)

    rollback = build_rollback_manifest(certificate, policy)
    write_json(rollback_dir / "rollback_manifest.json", rollback)

    inventory = build_inventory(root)
    write_json(actual_dir / "final_file_inventory.json", inventory)
    integrity = verify_inventory(root, inventory)
    write_json(actual_dir / "final_integrity_audit.json", integrity)

    acceptance = acceptance_test(
        readiness,
        integrity,
        certificate,
        manifest,
    )
    write_json(actual_dir / "final_acceptance_test.json", acceptance)

    release_bundle_path = bundle_dir / (
        "AI_STOCK_BOT_V105_FINAL_RELEASE_BUNDLE.zip"
    )
    bundle = create_bundle(root, release_bundle_path)

    state = (
        "PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE"
        if acceptance.get("passed") and bundle.get("created")
        else "PRODUCTION_READINESS_FINAL_RELEASE_REVIEW_REQUIRED"
    )
    observed_at = datetime.now(timezone.utc).isoformat()
    body = {
        "stage": "V105.64",
        "stage_range": "V105.33-V105.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed_at,
        "release_id": certificate.get("release_id"),
        "release_version": certificate.get("release_version"),
        "release_name": certificate.get("release_name"),
        "base_commit": policy.get("base_commit"),
        "integration_id": integration.get("integration_id"),
        "readiness": readiness,
        "certificate": certificate,
        "manifest": manifest,
        "inventory": {
            "file_count": inventory.get("file_count"),
            "total_size_bytes": inventory.get("total_size_bytes"),
        },
        "integrity": integrity,
        "acceptance": acceptance,
        "bundle": bundle,
        "rollback": rollback,
        "production_release_created": bundle.get("created") is True,
        "project_complete": state
            == "PRODUCTION_READINESS_FINAL_RELEASE_COMPLETE",
        "paper_trading_ready": readiness.get("passed") is True,
        "live_trading_ready": False,
        "approval_granted": False,
        "execution_authorized": False,
        "manual_approval_required": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "background_service_running": False,
        "windows_task_enabled": False,
        "next_phase": "PROJECT_COMPLETE_PAPER_TRADING_RELEASE",
    }
    body["final_release_result_sha256"] = digest(body)

    write_json(actual_dir / "production_readiness_final_release_result.json", body)
    append_jsonl(
        actual_dir / "final_release_ledger.jsonl",
        {
            "observed_at": observed_at,
            "release_id": body["release_id"],
            "release_version": body["release_version"],
            "state": state,
            "readiness_passed": readiness.get("passed"),
            "integrity_passed": integrity.get("passed"),
            "acceptance_passed": acceptance.get("passed"),
            "bundle_created": bundle.get("created"),
            "production_release_created": body["production_release_created"],
            "project_complete": body["project_complete"],
            "actual_orders_submitted": 0,
        },
    )
    return body
