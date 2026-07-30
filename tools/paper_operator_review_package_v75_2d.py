from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2D"
SCHEMA_VERSION = "v75.2d.paper_operator_review_package.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2c.paper_deployment_preflight.1"


class PaperOperatorReviewError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperOperatorReviewError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperOperatorReviewError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperOperatorReviewError("top-level JSON must be an object")
    return data


def verify_embedded_hash(obj: Dict[str, Any], field: str, label: str) -> None:
    observed = obj.get(field)
    if not isinstance(observed, str) or len(observed) != 64:
        raise PaperOperatorReviewError(f"{label} hash is invalid")
    copied = dict(obj)
    copied.pop(field, None)
    if observed != sha256_of(copied):
        raise PaperOperatorReviewError(f"{label} integrity verification failed")


def validate_preflight(preflight: Dict[str, Any]) -> None:
    if preflight.get("status") != "PASS":
        raise PaperOperatorReviewError("preflight status must be PASS")
    if preflight.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperOperatorReviewError("unsupported preflight schema_version")
    if preflight.get("preflight_state") != "READY_FOR_OPERATOR_REVIEW":
        raise PaperOperatorReviewError("preflight_state must be READY_FOR_OPERATOR_REVIEW")
    if preflight.get("approved_for_live") is not False:
        raise PaperOperatorReviewError("approved_for_live must be false")
    if preflight.get("network_used") is not False:
        raise PaperOperatorReviewError("network_used must be false")
    verify_embedded_hash(preflight, "paper_deployment_preflight_sha256", "preflight")

    review = preflight.get("operator_review")
    if not isinstance(review, dict):
        raise PaperOperatorReviewError("operator_review is required")
    if review.get("required") is not True or review.get("state") != "PENDING":
        raise PaperOperatorReviewError("operator review must be required and pending")
    if review.get("approval_recorded") is not False:
        raise PaperOperatorReviewError("operator approval must not already be recorded")

    gate = preflight.get("activation_gate")
    if not isinstance(gate, dict) or gate.get("activation_allowed") is not False:
        raise PaperOperatorReviewError("activation must remain blocked")
    if gate.get("next_version") != VERSION:
        raise PaperOperatorReviewError("activation_gate next_version must be 75.2D")

    safety = preflight.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise PaperOperatorReviewError("safety lock must be ENFORCED")
    for key in (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "external_side_effects_allowed",
    ):
        if safety.get(key) is not False:
            raise PaperOperatorReviewError(f"safety_lock {key} must be false")

    checks = preflight.get("preflight_checks")
    if not isinstance(checks, list) or len(checks) < 7:
        raise PaperOperatorReviewError("preflight checks are incomplete")
    required_states = {
        "DEPLOYMENT_BUNDLE_INTEGRITY": "PASS",
        "REQUIRED_FILES": "PASS",
        "OFFLINE_RUNTIME_LOCKS": "PASS",
        "LAUNCH_PLAN_SEQUENCE": "PASS",
        "DEPLOYMENT_LEDGER_SEQUENCE": "PASS",
        "OPERATOR_REVIEW_GATE": "REQUIRED",
        "PAPER_SESSION_ACTIVATION": "BLOCKED",
    }
    observed = {x.get("check"): x.get("state") for x in checks if isinstance(x, dict)}
    if observed != required_states:
        raise PaperOperatorReviewError("preflight check states are invalid")


def validate_account(account: Dict[str, Any], session_id: str) -> None:
    verify_embedded_hash(account, "account_state_sha256", "paper account state")
    if account.get("account_state") != "INITIALIZED":
        raise PaperOperatorReviewError("paper account must be INITIALIZED")
    if account.get("cash") != account.get("equity"):
        raise PaperOperatorReviewError("initial cash and equity must match")
    if account.get("starting_cash") != account.get("cash"):
        raise PaperOperatorReviewError("starting cash must equal current cash")
    for key in ("positions", "open_orders", "closed_orders"):
        if account.get(key) != []:
            raise PaperOperatorReviewError(f"initial {key} must be empty")
    if account.get("realized_pnl") != 0.0 or account.get("unrealized_pnl") != 0.0:
        raise PaperOperatorReviewError("initial PnL must be zero")
    if not session_id.startswith("PAPER-"):
        raise PaperOperatorReviewError("invalid paper session id")


def validate_health(health: Dict[str, Any], session_id: str) -> None:
    verify_embedded_hash(health, "health_check_sha256", "session health")
    if health.get("session_id") != session_id:
        raise PaperOperatorReviewError("session health id mismatch")
    if health.get("health_state") != "READY":
        raise PaperOperatorReviewError("session health must be READY")
    if health.get("paper_activation_state") != "NOT_ACTIVATED":
        raise PaperOperatorReviewError("paper session must not be activated")
    for key in ("account_initialized", "champion_attached", "rollback_manifest_attached"):
        if health.get(key) is not True:
            raise PaperOperatorReviewError(f"health {key} must be true")
    for key in ("live_orders_disabled", "network_disabled"):
        if health.get(key) is not True:
            raise PaperOperatorReviewError(f"health {key} must be true")
    if health.get("bootstrap_integrity") != "PASS":
        raise PaperOperatorReviewError("bootstrap integrity must be PASS")


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("operator_signature_required") is not True:
        raise PaperOperatorReviewError("operator_signature_required must be true")
    if config.get("automatic_approval_allowed") is not False:
        raise PaperOperatorReviewError("automatic approval must be disabled")
    if config.get("activation_allowed") is not False:
        raise PaperOperatorReviewError("activation_allowed must be false")
    if config.get("network_enabled") is not False:
        raise PaperOperatorReviewError("network_enabled must be false")
    decisions = config.get("allowed_operator_decisions")
    if decisions != ["APPROVE_PAPER", "REJECT", "HOLD"]:
        raise PaperOperatorReviewError("allowed operator decisions are invalid")
    checklist = config.get("required_review_items")
    if not isinstance(checklist, list) or len(checklist) < 5 or len(set(checklist)) != len(checklist):
        raise PaperOperatorReviewError("required_review_items are invalid")


def deterministic_review_id(preflight_id: str, source_hash: str, created_at: str) -> str:
    payload = f"{preflight_id}|{source_hash}|{created_at}|{VERSION}"
    return "POR-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_review_package(
    preflight: Dict[str, Any],
    account: Dict[str, Any],
    health: Dict[str, Any],
    config: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_preflight(preflight)
    validate_config(config)
    session_id = preflight["session_id"]
    validate_account(account, session_id)
    validate_health(health, session_id)
    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    review_id = deterministic_review_id(
        preflight["preflight_id"], preflight["paper_deployment_preflight_sha256"], created_at
    )
    checklist: List[Dict[str, Any]] = []
    for index, item in enumerate(config["required_review_items"], start=1):
        checklist.append({
            "review_index": index,
            "review_item": item,
            "state": "PENDING_OPERATOR_CONFIRMATION",
            "operator_confirmed": False,
        })

    warnings = [
        {
            "warning_index": 1,
            "code": "PAPER_SESSION_NOT_ACTIVATED",
            "severity": "INFO",
            "message": "Paper session activation remains blocked until a separate signed decision is validated.",
        },
        {
            "warning_index": 2,
            "code": "LIVE_TRADING_PROHIBITED",
            "severity": "CRITICAL",
            "message": "This package does not approve live trading, broker connectivity, or external order submission.",
        },
    ]
    decision_record = {
        "decision_state": "PENDING",
        "selected_decision": None,
        "allowed_decisions": config["allowed_operator_decisions"],
        "operator_name": None,
        "operator_signature": None,
        "signed_at": None,
        "reason": None,
        "signature_required": True,
        "decision_recorded": False,
    }
    ledger = [
        {"ledger_index": 1, "event": "PREFLIGHT_RESULT_VERIFIED", "state": "PASS", "review_id": review_id},
        {"ledger_index": 2, "event": "ACCOUNT_STATE_SUMMARIZED", "state": "CREATED", "review_id": review_id},
        {"ledger_index": 3, "event": "SESSION_HEALTH_SUMMARIZED", "state": "CREATED", "review_id": review_id},
        {"ledger_index": 4, "event": "OPERATOR_CHECKLIST_CREATED", "state": "PENDING", "review_id": review_id},
        {"ledger_index": 5, "event": "OPERATOR_DECISION_REQUESTED", "state": "PENDING", "review_id": review_id},
        {"ledger_index": 6, "event": "PAPER_ACTIVATION_HELD", "state": "BLOCKED", "review_id": review_id},
    ]

    result = {
        "status": "PASS",
        "decision": "paper_operator_review_package_created",
        "review_state": "AWAITING_OPERATOR_DECISION",
        "review_id": review_id,
        "preflight_id": preflight["preflight_id"],
        "bundle_id": preflight["bundle_id"],
        "session_id": session_id,
        "champion_candidate_id": preflight["champion_candidate_id"],
        "review_summary": {
            "verified_file_count": len(preflight["verified_files"]),
            "preflight_state": preflight["preflight_state"],
            "account_state": account["account_state"],
            "starting_cash": account["starting_cash"],
            "cash": account["cash"],
            "equity": account["equity"],
            "currency": account["currency"],
            "max_positions": account["max_positions"],
            "position_count": len(account["positions"]),
            "open_order_count": len(account["open_orders"]),
            "health_state": health["health_state"],
            "paper_activation_state": health["paper_activation_state"],
        },
        "review_checklist": checklist,
        "review_warnings": warnings,
        "operator_decision": decision_record,
        "review_ledger": ledger,
        "review_checklist_sha256": sha256_of(checklist),
        "review_ledger_sha256": sha256_of(ledger),
        "source_paper_deployment_preflight_sha256": preflight["paper_deployment_preflight_sha256"],
        "activation_gate": {
            "activation_allowed": False,
            "operator_decision_recorded": False,
            "operator_signature_verified": False,
            "next_version": "75.2E",
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "automatic_approval_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["paper_operator_review_package_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "paper_operator_review_package_v75_2d.json": result,
        "paper_operator_review_checklist_v75_2d.json": {
            "review_id": result["review_id"],
            "review_checklist": result["review_checklist"],
            "review_checklist_sha256": result["review_checklist_sha256"],
        },
        "paper_operator_review_ledger_v75_2d.json": {
            "review_id": result["review_id"],
            "review_ledger": result["review_ledger"],
            "review_ledger_sha256": result["review_ledger_sha256"],
        },
    }
    for filename, data in payloads.items():
        (output_dir / filename).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "paper_operator_review_package_v75_2d.sha256").write_text(
        result["paper_operator_review_package_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2D Paper Operator Review Package")
    p.add_argument("--input", required=True)
    p.add_argument("--account-state", required=True)
    p.add_argument("--session-health", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_review_package(
            read_json(Path(args.input)),
            read_json(Path(args.account_state)),
            read_json(Path(args.session_health)),
            read_json(Path(args.config)),
        )
        write_outputs(result, Path(args.output_dir))
        summary = {
            "status": result["status"],
            "decision": result["decision"],
            "review_state": result["review_state"],
            "review_id": result["review_id"],
            "preflight_id": result["preflight_id"],
            "session_id": result["session_id"],
            "champion_candidate_id": result["champion_candidate_id"],
            "review_item_count": len(result["review_checklist"]),
            "operator_decision_recorded": result["operator_decision"]["decision_recorded"],
            "activation_allowed": result["activation_gate"]["activation_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "paper_operator_review_package_sha256": result["paper_operator_review_package_sha256"],
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    except PaperOperatorReviewError as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_operator_review_package_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
