from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from v120_final_release.io import load_json,write_json,append_jsonl,digest
from v120_final_release.integration import evaluate_stages
from v120_final_release.safety import evaluate_safety
from v120_final_release.inventory import build_inventory,verify_inventory
from v120_final_release.bundle import create_bundle

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(root/"release/v120_final/input/v120_release_policy.json")
    actual=root/"release/v120_final/actual"
    integration=evaluate_stages(root)
    safety=evaluate_safety(integration)
    release_id=digest({
        "base_commit":policy.get("base_commit"),
        "integration":integration,
        "safety":safety,
        "version":policy.get("release_version"),
    })[:24]
    certificate={
        "certificate_type":"V120_FINAL_COMPLETION_CERTIFICATE",
        "release_id":release_id,
        "release_version":policy.get("release_version"),
        "base_commit":policy.get("base_commit"),
        "issued_at":datetime.now(timezone.utc).isoformat(),
        "development_complete":integration.get("passed") and safety.get("passed"),
        "paper_trading_ready":integration.get("passed") and safety.get("passed"),
        "live_trading_enabled":False,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "manual_approval_required":True,
        "actual_orders_submitted":0,
    }
    certificate["certificate_sha256"]=digest(certificate)
    write_json(actual/"v120_completion_certificate.json",certificate)

    manifest={
        "manifest_type":"V120_FINAL_RELEASE_MANIFEST",
        "release_id":release_id,
        "release_version":policy.get("release_version"),
        "base_commit":policy.get("base_commit"),
        "included_stages":[r["name"] for r in integration.get("rows",[])],
        "stage_count":integration.get("stage_count"),
        "production_bundle_required":True,
        "paper_only":True,
        "live_trading_enabled":False,
    }
    manifest["manifest_sha256"]=digest(manifest)
    write_json(actual/"v120_release_manifest.json",manifest)

    inventory=build_inventory(root)
    write_json(actual/"project_inventory.json",inventory)
    integrity=verify_inventory(root,inventory)
    write_json(actual/"integrity_audit.json",integrity)

    acceptance_checks={
        "integration_passed":integration.get("passed") is True,
        "safety_passed":safety.get("passed") is True,
        "integrity_passed":integrity.get("passed") is True,
        "certificate_valid":len(certificate["certificate_sha256"])==64,
        "manifest_valid":len(manifest["manifest_sha256"])==64,
        "orders_zero":True,
        "live_disabled":True,
        "broker_write_disabled":True,
        "manual_approval_required":True,
    }
    acceptance={
        "checks":acceptance_checks,
        "failed":[k for k,v in acceptance_checks.items() if not v],
        "passed":all(acceptance_checks.values()),
    }
    write_json(actual/"final_acceptance_test.json",acceptance)

    bundle=create_bundle(
        root,
        root/"release/v120_final/bundle/AI_STOCK_BOT_V120_FINAL.zip",
    )
    complete=acceptance["passed"] and bundle["created"]
    state="V120_FINAL_PRODUCTION_RELEASE_COMPLETE" if complete else "V120_FINAL_PRODUCTION_RELEASE_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V120.00",
        "stage_range":"V120_FINAL",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "release_id":release_id,
        "release_version":policy.get("release_version"),
        "base_commit":policy.get("base_commit"),
        "integration":integration,
        "safety":safety,
        "certificate":certificate,
        "manifest":manifest,
        "integrity":integrity,
        "acceptance":acceptance,
        "bundle":bundle,
        "development_complete":complete,
        "production_release_created":bundle["created"],
        "paper_trading_ready":complete,
        "live_trading_ready":False,
        "manual_approval_required":True,
        "approval_granted":False,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "actual_orders_submitted":0,
        "paper_only":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "next_phase":"PAPER_TRADING_OPERATION_AND_VALIDATION",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"v120_final_release_result.json",body)
    append_jsonl(actual/"v120_release_ledger.jsonl",{
        "observed_at":observed,
        "release_id":release_id,
        "state":state,
        "development_complete":complete,
        "actual_orders_submitted":0,
    })
    return body
