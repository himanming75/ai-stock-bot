from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

VERSION = "75.2C"
SCHEMA_VERSION = "v75.2c.paper_deployment_preflight.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2b.paper_deployment_bundle.1"


class PaperDeploymentPreflightError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperDeploymentPreflightError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperDeploymentPreflightError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperDeploymentPreflightError("top-level JSON must be an object")
    return data


def safe_repo_path(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        return False
    if len(normalized) >= 2 and normalized[1] == ":":
        return False
    return True


def verify_embedded_hash(obj: Dict[str, Any], field: str, label: str) -> None:
    observed = obj.get(field)
    if not isinstance(observed, str) or len(observed) != 64:
        raise PaperDeploymentPreflightError(f"{label} hash is invalid")
    copied = dict(obj)
    copied.pop(field, None)
    if observed != sha256_of(copied):
        raise PaperDeploymentPreflightError(f"{label} integrity verification failed")


def validate_source(bundle: Dict[str, Any]) -> None:
    if bundle.get("status") != "PASS":
        raise PaperDeploymentPreflightError("source status must be PASS")
    if bundle.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperDeploymentPreflightError("unsupported source schema_version")
    if bundle.get("deployment_state") != "READY_FOR_PAPER_DEPLOYMENT_PREFLIGHT":
        raise PaperDeploymentPreflightError(
            "deployment_state must be READY_FOR_PAPER_DEPLOYMENT_PREFLIGHT"
        )
    if bundle.get("session_mode") != "OFFLINE_PAPER":
        raise PaperDeploymentPreflightError("session_mode must be OFFLINE_PAPER")
    if bundle.get("approved_for_live") is not False:
        raise PaperDeploymentPreflightError("approved_for_live must be false")
    if bundle.get("network_used") is not False:
        raise PaperDeploymentPreflightError("network_used must be false")
    verify_embedded_hash(bundle, "paper_deployment_bundle_sha256", "deployment bundle")

    safety = bundle.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise PaperDeploymentPreflightError("safety lock must be ENFORCED")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "external_side_effects_allowed",
    ):
        if safety.get(key) is not False:
            raise PaperDeploymentPreflightError(f"safety_lock {key} must be false")

    gate = bundle.get("activation_gate")
    if not isinstance(gate, dict) or gate.get("activation_allowed") is not False:
        raise PaperDeploymentPreflightError("activation must remain blocked")
    if gate.get("next_version") != VERSION:
        raise PaperDeploymentPreflightError("activation_gate next_version must be 75.2C")

    runtime = bundle.get("runtime_manifest")
    if not isinstance(runtime, dict):
        raise PaperDeploymentPreflightError("runtime_manifest is required")
    verify_embedded_hash(runtime, "runtime_manifest_sha256", "runtime manifest")
    if runtime.get("deployment_mode") != "OFFLINE_PAPER":
        raise PaperDeploymentPreflightError("runtime must be OFFLINE_PAPER")
    if runtime.get("runtime_state") != "DEFINED_NOT_STARTED":
        raise PaperDeploymentPreflightError("runtime must not be started")
    for key in ("network_enabled", "live_orders_enabled", "broker_credentials_required"):
        if runtime.get(key) is not False:
            raise PaperDeploymentPreflightError(f"runtime {key} must be false")
    expected_env = {
        "AI_STOCK_BOT_MODE": "OFFLINE_PAPER",
        "AI_STOCK_BOT_NETWORK_ENABLED": "0",
        "AI_STOCK_BOT_LIVE_ORDERS_ENABLED": "0",
        "AI_STOCK_BOT_BROKER_CREDENTIALS_REQUIRED": "0",
    }
    if runtime.get("environment") != expected_env:
        raise PaperDeploymentPreflightError("runtime environment locks are invalid")

    inventory = bundle.get("file_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise PaperDeploymentPreflightError("file_inventory must be non-empty")
    for index, item in enumerate(inventory, start=1):
        if not isinstance(item, dict):
            raise PaperDeploymentPreflightError("inventory entries must be objects")
        if item.get("inventory_index") != index:
            raise PaperDeploymentPreflightError("inventory indexes must be sequential")
        if item.get("required") is not True:
            raise PaperDeploymentPreflightError("inventory files must be required")
        if item.get("verification_state") != "PENDING_PREFLIGHT":
            raise PaperDeploymentPreflightError("inventory state must be PENDING_PREFLIGHT")
        if not safe_repo_path(item.get("path", "")):
            raise PaperDeploymentPreflightError("unsafe repository-relative path")

    plan = bundle.get("launch_plan")
    expected_actions = [
        "VERIFY_DEPLOYMENT_BUNDLE_INTEGRITY",
        "VERIFY_REQUIRED_FILES",
        "VERIFY_OFFLINE_RUNTIME_LOCKS",
        "REQUEST_OPERATOR_REVIEW",
        "HOLD_PAPER_SESSION_ACTIVATION",
    ]
    if not isinstance(plan, list) or [x.get("action") for x in plan if isinstance(x, dict)] != expected_actions:
        raise PaperDeploymentPreflightError("launch plan sequence is invalid")
    if [x.get("step") for x in plan] != list(range(1, 6)):
        raise PaperDeploymentPreflightError("launch plan steps must be sequential")

    ledger = bundle.get("deployment_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise PaperDeploymentPreflightError("deployment_ledger is required")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise PaperDeploymentPreflightError("deployment ledger indexes must be sequential")


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("repository_root_required") is not True:
        raise PaperDeploymentPreflightError("repository_root_required must be true")
    if config.get("verify_required_files") is not True:
        raise PaperDeploymentPreflightError("verify_required_files must be true")
    if config.get("operator_review_required") is not True:
        raise PaperDeploymentPreflightError("operator_review_required must be true")
    if config.get("activation_allowed") is not False:
        raise PaperDeploymentPreflightError("activation_allowed must be false")
    if config.get("network_enabled") is not False:
        raise PaperDeploymentPreflightError("network_enabled must be false")
    forbidden = config.get("forbidden_environment_variables")
    if not isinstance(forbidden, list) or not forbidden:
        raise PaperDeploymentPreflightError("forbidden_environment_variables required")


def deterministic_preflight_id(bundle_id: str, source_hash: str, created_at: str) -> str:
    payload = f"{bundle_id}|{source_hash}|{created_at}|{VERSION}"
    return "PDP-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_preflight(
    bundle: Dict[str, Any],
    config: Dict[str, Any],
    repository_root: Path,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(bundle)
    validate_config(config)
    root = repository_root.resolve()
    if not root.exists() or not root.is_dir():
        raise PaperDeploymentPreflightError("repository root does not exist")
    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    checks: List[Dict[str, Any]] = []
    checks.append({"check_index": 1, "check": "DEPLOYMENT_BUNDLE_INTEGRITY", "state": "PASS"})

    verified_files = []
    for item in bundle["file_inventory"]:
        rel = item["path"]
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise PaperDeploymentPreflightError("required file escapes repository root") from exc
        exists = candidate.is_file()
        verified_files.append({
            "inventory_index": item["inventory_index"],
            "path": rel,
            "required": True,
            "exists": exists,
            "verification_state": "VERIFIED" if exists else "MISSING",
        })
    missing = [x["path"] for x in verified_files if not x["exists"]]
    if missing:
        raise PaperDeploymentPreflightError("required files missing: " + ", ".join(missing))
    checks.append({"check_index": 2, "check": "REQUIRED_FILES", "state": "PASS", "verified_count": len(verified_files)})
    checks.append({"check_index": 3, "check": "OFFLINE_RUNTIME_LOCKS", "state": "PASS"})
    checks.append({"check_index": 4, "check": "LAUNCH_PLAN_SEQUENCE", "state": "PASS"})
    checks.append({"check_index": 5, "check": "DEPLOYMENT_LEDGER_SEQUENCE", "state": "PASS"})
    checks.append({"check_index": 6, "check": "OPERATOR_REVIEW_GATE", "state": "REQUIRED"})
    checks.append({"check_index": 7, "check": "PAPER_SESSION_ACTIVATION", "state": "BLOCKED"})

    preflight_id = deterministic_preflight_id(
        bundle["bundle_id"], bundle["paper_deployment_bundle_sha256"], created_at
    )
    ledger = [
        {"ledger_index": 1, "event": "DEPLOYMENT_BUNDLE_VERIFIED", "state": "PASS", "preflight_id": preflight_id},
        {"ledger_index": 2, "event": "REQUIRED_FILES_VERIFIED", "state": "PASS", "preflight_id": preflight_id},
        {"ledger_index": 3, "event": "OFFLINE_LOCKS_VERIFIED", "state": "PASS", "preflight_id": preflight_id},
        {"ledger_index": 4, "event": "OPERATOR_REVIEW_REQUESTED", "state": "PENDING", "preflight_id": preflight_id},
        {"ledger_index": 5, "event": "PAPER_ACTIVATION_HELD", "state": "BLOCKED", "preflight_id": preflight_id},
    ]
    result = {
        "status": "PASS",
        "decision": "paper_deployment_preflight_passed",
        "preflight_state": "READY_FOR_OPERATOR_REVIEW",
        "preflight_id": preflight_id,
        "bundle_id": bundle["bundle_id"],
        "session_id": bundle["session_id"],
        "champion_candidate_id": bundle["champion_candidate_id"],
        "verified_files": verified_files,
        "preflight_checks": checks,
        "preflight_ledger": ledger,
        "preflight_checklist_sha256": sha256_of(checks),
        "preflight_ledger_sha256": sha256_of(ledger),
        "source_paper_deployment_bundle_sha256": bundle["paper_deployment_bundle_sha256"],
        "operator_review": {"required": True, "state": "PENDING", "approval_recorded": False},
        "activation_gate": {"activation_allowed": False, "next_version": "75.2D", "operator_review_required": True},
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["paper_deployment_preflight_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "paper_deployment_preflight_v75_2c.json": result,
        "paper_deployment_preflight_checklist_v75_2c.json": {
            "preflight_id": result["preflight_id"],
            "preflight_checks": result["preflight_checks"],
            "preflight_checklist_sha256": result["preflight_checklist_sha256"],
        },
        "paper_deployment_preflight_ledger_v75_2c.json": {
            "preflight_id": result["preflight_id"],
            "preflight_ledger": result["preflight_ledger"],
            "preflight_ledger_sha256": result["preflight_ledger_sha256"],
        },
    }
    for filename, data in payloads.items():
        (output_dir / filename).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "paper_deployment_preflight_v75_2c.sha256").write_text(
        result["paper_deployment_preflight_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2C Paper Deployment Preflight Validator")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--repository-root", default=".")
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_preflight(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            Path(args.repository_root),
        )
        write_outputs(result, Path(args.output_dir))
        summary = {
            "status": result["status"],
            "decision": result["decision"],
            "preflight_state": result["preflight_state"],
            "preflight_id": result["preflight_id"],
            "bundle_id": result["bundle_id"],
            "session_id": result["session_id"],
            "verified_file_count": len(result["verified_files"]),
            "operator_review_required": result["operator_review"]["required"],
            "activation_allowed": result["activation_gate"]["activation_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "paper_deployment_preflight_sha256": result["paper_deployment_preflight_sha256"],
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except PaperDeploymentPreflightError as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_deployment_preflight_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
