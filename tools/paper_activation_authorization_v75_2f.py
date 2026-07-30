from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2F"
SCHEMA_VERSION = "v75.2f.paper_activation_authorization.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2e.paper_operator_decision_record.1"


class PaperActivationAuthorizationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperActivationAuthorizationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperActivationAuthorizationError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperActivationAuthorizationError("top-level JSON must be an object")
    return data


def verify_embedded_hash(obj: Dict[str, Any], field: str, label: str) -> None:
    observed = obj.get(field)
    if not isinstance(observed, str) or len(observed) != 64:
        raise PaperActivationAuthorizationError(f"{label} hash is invalid")
    copied = dict(obj)
    copied.pop(field, None)
    if observed != sha256_of(copied):
        raise PaperActivationAuthorizationError(f"{label} integrity verification failed")


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise PaperActivationAuthorizationError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperActivationAuthorizationError("unsupported source schema_version")
    if source.get("selected_decision") != "APPROVE_PAPER":
        raise PaperActivationAuthorizationError("operator decision must be APPROVE_PAPER")
    if source.get("decision_state") != "APPROVED_FOR_PAPER_ACTIVATION_PREPARATION":
        raise PaperActivationAuthorizationError("decision_state is not approved for preparation")
    if source.get("next_state") != "READY_FOR_PAPER_ACTIVATION_AUTHORIZATION":
        raise PaperActivationAuthorizationError("source next_state is invalid")
    if source.get("approved_for_live") is not False or source.get("network_used") is not False:
        raise PaperActivationAuthorizationError("live approval and network use must remain false")
    verify_embedded_hash(source, "paper_operator_decision_record_sha256", "decision record")

    operator = source.get("operator_record")
    if not isinstance(operator, dict) or operator.get("signature_verified") is not True:
        raise PaperActivationAuthorizationError("operator signature must be verified")
    evidence = {
        "decision_id": source.get("decision_id"),
        "review_id": source.get("review_id"),
        "selected_decision": source.get("selected_decision"),
        "operator_name": operator.get("operator_name"),
        "operator_signature": operator.get("operator_signature"),
        "reason": operator.get("reason"),
        "signed_at": operator.get("signed_at"),
        "source_review_sha256": source.get("source_paper_operator_review_package_sha256"),
    }
    if operator.get("signature_evidence_sha256") != sha256_of(evidence):
        raise PaperActivationAuthorizationError("operator signature evidence integrity failed")

    checklist = source.get("confirmed_checklist")
    if not isinstance(checklist, list) or not checklist:
        raise PaperActivationAuthorizationError("confirmed checklist is required")
    if source.get("confirmed_checklist_sha256") != sha256_of(checklist):
        raise PaperActivationAuthorizationError("confirmed checklist integrity failed")
    if any(x.get("operator_confirmed") is not True or x.get("state") != "CONFIRMED" for x in checklist):
        raise PaperActivationAuthorizationError("all checklist items must be confirmed")

    ledger = source.get("decision_ledger")
    if not isinstance(ledger, list) or not ledger:
        raise PaperActivationAuthorizationError("decision ledger is required")
    if source.get("decision_ledger_sha256") != sha256_of(ledger):
        raise PaperActivationAuthorizationError("decision ledger integrity failed")
    if [x.get("ledger_index") for x in ledger] != list(range(1, len(ledger) + 1)):
        raise PaperActivationAuthorizationError("decision ledger indexes must be sequential")

    gate = source.get("activation_gate")
    if not isinstance(gate, dict):
        raise PaperActivationAuthorizationError("activation gate is required")
    if gate.get("paper_activation_preparation_allowed") is not True:
        raise PaperActivationAuthorizationError("paper activation preparation must be allowed")
    if gate.get("activation_allowed") is not False or gate.get("live_activation_allowed") is not False:
        raise PaperActivationAuthorizationError("actual activation must remain blocked")
    if gate.get("next_version") != VERSION:
        raise PaperActivationAuthorizationError("activation_gate next_version must be 75.2F")

    safety = source.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise PaperActivationAuthorizationError("safety lock must be ENFORCED")
    for key in ("network_enabled", "live_orders_enabled", "broker_credentials_required",
                "external_side_effects_allowed", "automatic_approval_allowed"):
        if safety.get(key) is not False:
            raise PaperActivationAuthorizationError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    required_true = (
        "require_signed_operator_decision",
        "require_confirmed_checklist",
        "require_offline_paper_mode",
        "single_use_authorization",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise PaperActivationAuthorizationError(f"{key} must be true")
    required_false = (
        "network_enabled",
        "live_orders_enabled",
        "broker_credentials_required",
        "automatic_activation_allowed",
        "live_trading_approval_allowed",
    )
    for key in required_false:
        if config.get(key) is not False:
            raise PaperActivationAuthorizationError(f"{key} must be false")
    ttl = config.get("authorization_ttl_seconds")
    if not isinstance(ttl, int) or ttl < 60 or ttl > 86400:
        raise PaperActivationAuthorizationError("authorization_ttl_seconds is invalid")


def deterministic_authorization_id(decision_id: str, source_hash: str, created_at: str) -> str:
    payload = f"{decision_id}|{source_hash}|{created_at}|{VERSION}"
    return "PAA-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_authorization(
    source: Dict[str, Any],
    config: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    authorization_id = deterministic_authorization_id(
        source["decision_id"],
        source["paper_operator_decision_record_sha256"],
        created_at,
    )
    token_payload = {
        "authorization_id": authorization_id,
        "decision_id": source["decision_id"],
        "session_id": source["session_id"],
        "scope": "OFFLINE_PAPER_ACTIVATION_ONLY",
        "single_use": True,
        "issued_at": created_at,
        "ttl_seconds": config["authorization_ttl_seconds"],
    }
    activation_token = hashlib.sha256(canonical_json(token_payload).encode("utf-8")).hexdigest()
    authorization_checks = [
        {"check_index": 1, "check": "DECISION_RECORD_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "OPERATOR_DECISION_APPROVE_PAPER", "state": "PASS"},
        {"check_index": 3, "check": "OPERATOR_SIGNATURE_EVIDENCE", "state": "PASS"},
        {"check_index": 4, "check": "CONFIRMED_CHECKLIST", "state": "PASS"},
        {"check_index": 5, "check": "OFFLINE_PAPER_SAFETY_LOCKS", "state": "PASS"},
        {"check_index": 6, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
        {"check_index": 7, "check": "ACTIVATION_EXECUTION", "state": "NOT_EXECUTED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "SIGNED_DECISION_VERIFIED", "state": "PASS", "authorization_id": authorization_id},
        {"ledger_index": 2, "event": "PAPER_SCOPE_VERIFIED", "state": "PASS", "authorization_id": authorization_id},
        {"ledger_index": 3, "event": "ACTIVATION_TOKEN_ISSUED", "state": "ISSUED_NOT_CONSUMED", "authorization_id": authorization_id},
        {"ledger_index": 4, "event": "LIVE_TRADING_LOCK_RECONFIRMED", "state": "ENFORCED", "authorization_id": authorization_id},
        {"ledger_index": 5, "event": "PAPER_ACTIVATION_EXECUTION_HELD", "state": "READY_FOR_SEPARATE_EXECUTION", "authorization_id": authorization_id},
    ]
    result = {
        "status": "PASS",
        "decision": "paper_activation_authorization_created",
        "authorization_state": "AUTHORIZED_NOT_ACTIVATED",
        "authorization_id": authorization_id,
        "decision_id": source["decision_id"],
        "review_id": source["review_id"],
        "preflight_id": source["preflight_id"],
        "bundle_id": source["bundle_id"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "authorization_scope": "OFFLINE_PAPER_ACTIVATION_ONLY",
        "activation_token": {
            "token_sha256": activation_token,
            "single_use": True,
            "consumed": False,
            "issued_at": created_at,
            "ttl_seconds": config["authorization_ttl_seconds"],
        },
        "authorization_checks": authorization_checks,
        "authorization_ledger": ledger,
        "authorization_checks_sha256": sha256_of(authorization_checks),
        "authorization_ledger_sha256": sha256_of(ledger),
        "source_paper_operator_decision_record_sha256": source["paper_operator_decision_record_sha256"],
        "activation_gate": {
            "paper_activation_authorized": True,
            "activation_allowed": False,
            "activation_executed": False,
            "live_activation_allowed": False,
            "token_consumed": False,
            "next_version": "75.2G",
        },
        "runtime_policy": {
            "mode": "OFFLINE_PAPER",
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "automatic_activation_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["paper_activation_authorization_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "paper_activation_authorization_v75_2f.json": result,
        "paper_activation_authorization_checks_v75_2f.json": {
            "authorization_id": result["authorization_id"],
            "authorization_checks": result["authorization_checks"],
            "authorization_checks_sha256": result["authorization_checks_sha256"],
        },
        "paper_activation_authorization_ledger_v75_2f.json": {
            "authorization_id": result["authorization_id"],
            "authorization_ledger": result["authorization_ledger"],
            "authorization_ledger_sha256": result["authorization_ledger_sha256"],
        },
        "paper_activation_token_v75_2f.json": {
            "authorization_id": result["authorization_id"],
            "session_id": result["session_id"],
            "authorization_scope": result["authorization_scope"],
            "activation_token": result["activation_token"],
        },
    }
    for filename, data in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (output_dir / "paper_activation_authorization_v75_2f.sha256").write_text(
        result["paper_activation_authorization_sha256"] + "\n", encoding="utf-8"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2F Paper Activation Authorization Package")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_authorization(read_json(Path(args.input)), read_json(Path(args.config)))
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "authorization_id": result["authorization_id"],
            "authorization_state": result["authorization_state"],
            "authorization_scope": result["authorization_scope"],
            "session_id": result["session_id"],
            "paper_activation_authorized": result["activation_gate"]["paper_activation_authorized"],
            "activation_allowed": result["activation_gate"]["activation_allowed"],
            "activation_executed": result["activation_gate"]["activation_executed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "paper_activation_authorization_sha256": result["paper_activation_authorization_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (PaperActivationAuthorizationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "paper_activation_authorization_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
