from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "75.2B"
SCHEMA_VERSION = "v75.2b.paper_deployment_bundle.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2a.paper_session_bootstrap.1"


class PaperDeploymentBundleError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperDeploymentBundleError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperDeploymentBundleError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperDeploymentBundleError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise PaperDeploymentBundleError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperDeploymentBundleError("unsupported source schema_version")
    if source.get("bootstrap_state") != "READY_FOR_PAPER_DEPLOYMENT_BUNDLE":
        raise PaperDeploymentBundleError(
            "bootstrap_state must be READY_FOR_PAPER_DEPLOYMENT_BUNDLE"
        )
    if source.get("session_mode") != "OFFLINE_PAPER":
        raise PaperDeploymentBundleError("session_mode must be OFFLINE_PAPER")
    if source.get("promotion_scope") != "PROVISIONAL_PAPER_ONLY":
        raise PaperDeploymentBundleError(
            "promotion_scope must be PROVISIONAL_PAPER_ONLY"
        )
    if source.get("approved_for_live") is not False:
        raise PaperDeploymentBundleError("source approved_for_live must be false")
    if source.get("network_used") is not False:
        raise PaperDeploymentBundleError("source network_used must be false")

    safety_lock = source.get("safety_lock")
    if not isinstance(safety_lock, dict):
        raise PaperDeploymentBundleError("safety_lock is required")
    if safety_lock.get("lock_state") != "ENFORCED":
        raise PaperDeploymentBundleError("safety lock must be ENFORCED")
    if safety_lock.get("network_enabled") is not False:
        raise PaperDeploymentBundleError("network_enabled must be false")
    if safety_lock.get("live_orders_enabled") is not False:
        raise PaperDeploymentBundleError("live_orders_enabled must be false")
    if safety_lock.get("external_side_effects_allowed") is not False:
        raise PaperDeploymentBundleError(
            "external_side_effects_allowed must be false"
        )

    activation_gate = source.get("activation_gate")
    if not isinstance(activation_gate, dict):
        raise PaperDeploymentBundleError("activation_gate is required")
    if activation_gate.get("activation_allowed") is not False:
        raise PaperDeploymentBundleError("activation_allowed must be false")
    if activation_gate.get("next_version") != VERSION:
        raise PaperDeploymentBundleError("activation_gate next_version must be 75.2B")

    session_id = source.get("session_id")
    champion_id = source.get("champion_candidate_id")
    if not isinstance(session_id, str) or not session_id.startswith("PAPER-"):
        raise PaperDeploymentBundleError("valid PAPER session_id is required")
    if not champion_id:
        raise PaperDeploymentBundleError("champion_candidate_id is required")

    observed_hash = source.get("paper_session_bootstrap_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise PaperDeploymentBundleError(
            "paper_session_bootstrap_sha256 is invalid"
        )
    copied = dict(source)
    copied.pop("paper_session_bootstrap_sha256", None)
    if observed_hash != sha256_of(copied):
        raise PaperDeploymentBundleError(
            "paper session bootstrap integrity verification failed"
        )


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("deployment_mode") != "OFFLINE_PAPER":
        raise PaperDeploymentBundleError(
            "deployment_mode must be OFFLINE_PAPER"
        )
    if config.get("network_enabled") is not False:
        raise PaperDeploymentBundleError("network_enabled must be false")
    if config.get("live_orders_enabled") is not False:
        raise PaperDeploymentBundleError("live_orders_enabled must be false")
    if config.get("broker_credentials_required") is not False:
        raise PaperDeploymentBundleError(
            "broker_credentials_required must be false"
        )
    if config.get("operator_review_required") is not True:
        raise PaperDeploymentBundleError(
            "operator_review_required must be true"
        )

    python_command = config.get("python_command")
    if not isinstance(python_command, str) or not python_command.strip():
        raise PaperDeploymentBundleError("python_command is required")

    required_files = config.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        raise PaperDeploymentBundleError("required_files must be a non-empty list")
    for item in required_files:
        if not isinstance(item, str) or not item.strip():
            raise PaperDeploymentBundleError(
                "required_files entries must be non-empty strings"
            )
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            raise PaperDeploymentBundleError(
                "required_files must use safe repository-relative paths"
            )


def deterministic_bundle_id(session_id: str, source_hash: str, created_at: str) -> str:
    payload = f"{session_id}|{source_hash}|{created_at}|{VERSION}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"PDB-{digest}"


def build_bundle(
    source: Dict[str, Any],
    config: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    session_id = source["session_id"]
    source_hash = source["paper_session_bootstrap_sha256"]
    bundle_id = deterministic_bundle_id(session_id, source_hash, created_at)

    file_inventory = [
        {
            "inventory_index": index,
            "path": path,
            "required": True,
            "verification_state": "PENDING_PREFLIGHT",
        }
        for index, path in enumerate(config["required_files"], start=1)
    ]

    runtime_manifest = {
        "bundle_id": bundle_id,
        "session_id": session_id,
        "deployment_mode": "OFFLINE_PAPER",
        "python_command": config["python_command"],
        "environment": {
            "AI_STOCK_BOT_MODE": "OFFLINE_PAPER",
            "AI_STOCK_BOT_NETWORK_ENABLED": "0",
            "AI_STOCK_BOT_LIVE_ORDERS_ENABLED": "0",
            "AI_STOCK_BOT_BROKER_CREDENTIALS_REQUIRED": "0",
        },
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "runtime_state": "DEFINED_NOT_STARTED",
    }
    runtime_manifest["runtime_manifest_sha256"] = sha256_of(runtime_manifest)

    launch_plan = [
        {
            "step": 1,
            "action": "VERIFY_DEPLOYMENT_BUNDLE_INTEGRITY",
            "state": "PENDING_PREFLIGHT",
        },
        {
            "step": 2,
            "action": "VERIFY_REQUIRED_FILES",
            "state": "PENDING_PREFLIGHT",
        },
        {
            "step": 3,
            "action": "VERIFY_OFFLINE_RUNTIME_LOCKS",
            "state": "PENDING_PREFLIGHT",
        },
        {
            "step": 4,
            "action": "REQUEST_OPERATOR_REVIEW",
            "state": "PENDING_PREFLIGHT",
        },
        {
            "step": 5,
            "action": "HOLD_PAPER_SESSION_ACTIVATION",
            "state": "BLOCKED_UNTIL_REVIEW",
        },
    ]

    ledger = [
        {
            "ledger_index": 1,
            "event": "PAPER_BOOTSTRAP_VERIFIED",
            "bundle_id": bundle_id,
            "state": "PASS",
        },
        {
            "ledger_index": 2,
            "event": "DEPLOYMENT_FILE_INVENTORY_CREATED",
            "bundle_id": bundle_id,
            "state": "CREATED",
        },
        {
            "ledger_index": 3,
            "event": "PAPER_RUNTIME_MANIFEST_CREATED",
            "bundle_id": bundle_id,
            "state": "CREATED",
        },
        {
            "ledger_index": 4,
            "event": "PAPER_LAUNCH_PLAN_CREATED",
            "bundle_id": bundle_id,
            "state": "CREATED",
        },
        {
            "ledger_index": 5,
            "event": "PAPER_DEPLOYMENT_BUNDLE_CREATED",
            "bundle_id": bundle_id,
            "state": "READY_FOR_PREFLIGHT",
        },
    ]

    bundle = {
        "status": "PASS",
        "decision": "paper_deployment_bundle_created",
        "deployment_state": "READY_FOR_PAPER_DEPLOYMENT_PREFLIGHT",
        "bundle_id": bundle_id,
        "session_id": session_id,
        "session_mode": "OFFLINE_PAPER",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": source["champion_candidate_id"],
        "runner_up_candidate_id": source.get("runner_up_candidate_id"),
        "file_inventory": file_inventory,
        "runtime_manifest": runtime_manifest,
        "launch_plan": launch_plan,
        "deployment_ledger": ledger,
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "activation_gate": {
            "activation_allowed": False,
            "operator_review_required": True,
            "preflight_required": True,
            "next_version": "75.2C",
        },
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_paper_session_bootstrap_sha256": source_hash,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    bundle["file_inventory_sha256"] = sha256_of(file_inventory)
    bundle["launch_plan_sha256"] = sha256_of(launch_plan)
    bundle["deployment_ledger_sha256"] = sha256_of(ledger)
    bundle["paper_deployment_bundle_sha256"] = sha256_of(bundle)
    return bundle


def write_outputs(bundle: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "paper_deployment_bundle_v75_2b.json": bundle,
        "paper_deployment_file_inventory_v75_2b.json": {
            "bundle_id": bundle["bundle_id"],
            "file_inventory": bundle["file_inventory"],
            "file_inventory_sha256": bundle["file_inventory_sha256"],
        },
        "paper_runtime_manifest_v75_2b.json": bundle["runtime_manifest"],
        "paper_deployment_launch_plan_v75_2b.json": {
            "bundle_id": bundle["bundle_id"],
            "launch_plan": bundle["launch_plan"],
            "launch_plan_sha256": bundle["launch_plan_sha256"],
        },
        "paper_deployment_ledger_v75_2b.json": {
            "bundle_id": bundle["bundle_id"],
            "deployment_ledger": bundle["deployment_ledger"],
            "deployment_ledger_sha256": bundle["deployment_ledger_sha256"],
        },
    }
    for filename, data in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "paper_deployment_bundle_v75_2b.sha256").write_text(
        bundle["paper_deployment_bundle_sha256"] + "\n",
        encoding="utf-8",
    )


def run(input_path: Path, config_path: Path, output_dir: Path) -> Dict[str, Any]:
    source = read_json(input_path)
    config = read_json(config_path)
    bundle = build_bundle(source, config)
    write_outputs(bundle, output_dir)
    return bundle


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2B Paper Deployment Bundle Builder"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        bundle = run(args.input, args.config, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_deployment_bundle_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": bundle["status"],
        "decision": bundle["decision"],
        "deployment_state": bundle["deployment_state"],
        "bundle_id": bundle["bundle_id"],
        "session_id": bundle["session_id"],
        "champion_candidate_id": bundle["champion_candidate_id"],
        "required_file_count": len(bundle["file_inventory"]),
        "activation_allowed": bundle["activation_gate"]["activation_allowed"],
        "approved_for_live": bundle["approved_for_live"],
        "network_used": bundle["network_used"],
        "paper_deployment_bundle_sha256": bundle[
            "paper_deployment_bundle_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
