from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2E"
SCHEMA_VERSION = "v75.2e.paper_operator_decision_record.1"
SUPPORTED_SOURCE_SCHEMA = "v75.2d.paper_operator_review_package.1"
ALLOWED_DECISIONS = ["APPROVE_PAPER", "REJECT", "HOLD"]


class PaperOperatorDecisionError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PaperOperatorDecisionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PaperOperatorDecisionError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PaperOperatorDecisionError("top-level JSON must be an object")
    return data


def verify_embedded_hash(obj: Dict[str, Any], field: str, label: str) -> None:
    observed = obj.get(field)
    if not isinstance(observed, str) or len(observed) != 64:
        raise PaperOperatorDecisionError(f"{label} hash is invalid")
    copied = dict(obj)
    copied.pop(field, None)
    if observed != sha256_of(copied):
        raise PaperOperatorDecisionError(f"{label} integrity verification failed")


def validate_review_package(review: Dict[str, Any]) -> None:
    if review.get("status") != "PASS":
        raise PaperOperatorDecisionError("review package status must be PASS")
    if review.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PaperOperatorDecisionError("unsupported review package schema_version")
    if review.get("review_state") != "AWAITING_OPERATOR_DECISION":
        raise PaperOperatorDecisionError("review_state must be AWAITING_OPERATOR_DECISION")
    if review.get("approved_for_live") is not False or review.get("network_used") is not False:
        raise PaperOperatorDecisionError("live approval and network use must remain false")
    verify_embedded_hash(review, "paper_operator_review_package_sha256", "review package")

    pending = review.get("operator_decision")
    if not isinstance(pending, dict):
        raise PaperOperatorDecisionError("operator_decision section is required")
    if pending.get("decision_state") != "PENDING" or pending.get("decision_recorded") is not False:
        raise PaperOperatorDecisionError("source decision must be pending and unrecorded")
    if pending.get("allowed_decisions") != ALLOWED_DECISIONS:
        raise PaperOperatorDecisionError("source allowed decisions are invalid")

    gate = review.get("activation_gate")
    if not isinstance(gate, dict) or gate.get("activation_allowed") is not False:
        raise PaperOperatorDecisionError("source activation must remain blocked")
    if gate.get("next_version") != VERSION:
        raise PaperOperatorDecisionError("activation_gate next_version must be 75.2E")

    safety = review.get("safety_lock")
    if not isinstance(safety, dict) or safety.get("lock_state") != "ENFORCED":
        raise PaperOperatorDecisionError("safety lock must be ENFORCED")
    for key in ("network_enabled", "live_orders_enabled", "broker_credentials_required", "external_side_effects_allowed", "automatic_approval_allowed"):
        if safety.get(key) is not False:
            raise PaperOperatorDecisionError(f"safety_lock {key} must be false")

    checklist = review.get("review_checklist")
    if not isinstance(checklist, list) or not checklist:
        raise PaperOperatorDecisionError("review checklist is required")
    if [x.get("review_index") for x in checklist if isinstance(x, dict)] != list(range(1, len(checklist) + 1)):
        raise PaperOperatorDecisionError("review checklist indexes must be sequential")
    if any(x.get("state") != "PENDING_OPERATOR_CONFIRMATION" or x.get("operator_confirmed") is not False for x in checklist):
        raise PaperOperatorDecisionError("source checklist must remain pending")


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("allowed_operator_decisions") != ALLOWED_DECISIONS:
        raise PaperOperatorDecisionError("configured decisions are invalid")
    for key in ("operator_name_required", "operator_signature_required", "decision_reason_required", "all_checklist_items_required"):
        if config.get(key) is not True:
            raise PaperOperatorDecisionError(f"{key} must be true")
    for key in ("automatic_approval_allowed", "live_trading_approval_allowed", "network_enabled"):
        if config.get(key) is not False:
            raise PaperOperatorDecisionError(f"{key} must be false")


def parse_iso8601(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperOperatorDecisionError("signed_at is required")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PaperOperatorDecisionError("signed_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PaperOperatorDecisionError("signed_at must include timezone")
    return parsed.isoformat()


def validate_decision_input(decision_input: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    decision = decision_input.get("selected_decision")
    if decision not in ALLOWED_DECISIONS:
        raise PaperOperatorDecisionError("selected_decision must be APPROVE_PAPER, REJECT, or HOLD")
    operator_name = decision_input.get("operator_name")
    signature = decision_input.get("operator_signature")
    reason = decision_input.get("reason")
    if not isinstance(operator_name, str) or len(operator_name.strip()) < 2:
        raise PaperOperatorDecisionError("operator_name is required")
    if not isinstance(signature, str) or len(signature.strip()) < 4:
        raise PaperOperatorDecisionError("operator_signature is required")
    if not isinstance(reason, str) or len(reason.strip()) < 5:
        raise PaperOperatorDecisionError("decision reason is required")
    signed_at = parse_iso8601(decision_input.get("signed_at"))

    confirmations = decision_input.get("checklist_confirmations")
    expected = review["review_checklist"]
    if not isinstance(confirmations, list) or len(confirmations) != len(expected):
        raise PaperOperatorDecisionError("all checklist confirmations are required")
    normalized_confirmations: List[Dict[str, Any]] = []
    for expected_item, provided in zip(expected, confirmations):
        if not isinstance(provided, dict):
            raise PaperOperatorDecisionError("checklist confirmations must be objects")
        if provided.get("review_index") != expected_item["review_index"] or provided.get("review_item") != expected_item["review_item"]:
            raise PaperOperatorDecisionError("checklist confirmation does not match review package")
        if provided.get("operator_confirmed") is not True:
            raise PaperOperatorDecisionError("every checklist item must be confirmed")
        normalized_confirmations.append({
            "review_index": expected_item["review_index"],
            "review_item": expected_item["review_item"],
            "operator_confirmed": True,
            "state": "CONFIRMED",
        })
    return {
        "selected_decision": decision,
        "operator_name": operator_name.strip(),
        "operator_signature": signature.strip(),
        "reason": reason.strip(),
        "signed_at": signed_at,
        "checklist_confirmations": normalized_confirmations,
    }


def deterministic_decision_id(review_id: str, source_hash: str, decision: str, signed_at: str) -> str:
    payload = f"{review_id}|{source_hash}|{decision}|{signed_at}|{VERSION}"
    return "POD-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_decision_record(review: Dict[str, Any], decision_input: Dict[str, Any], config: Dict[str, Any], created_at: Optional[str] = None) -> Dict[str, Any]:
    validate_review_package(review)
    validate_config(config)
    normalized = validate_decision_input(decision_input, review)
    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    selected = normalized["selected_decision"]
    if selected == "APPROVE_PAPER":
        decision_state = "APPROVED_FOR_PAPER_ACTIVATION_PREPARATION"
        next_state = "READY_FOR_PAPER_ACTIVATION_AUTHORIZATION"
        preparation_allowed = True
    elif selected == "REJECT":
        decision_state = "REJECTED"
        next_state = "PAPER_DEPLOYMENT_REJECTED"
        preparation_allowed = False
    else:
        decision_state = "HELD"
        next_state = "PAPER_DEPLOYMENT_ON_HOLD"
        preparation_allowed = False

    decision_id = deterministic_decision_id(review["review_id"], review["paper_operator_review_package_sha256"], selected, normalized["signed_at"])
    signed_payload = {
        "decision_id": decision_id,
        "review_id": review["review_id"],
        "selected_decision": selected,
        "operator_name": normalized["operator_name"],
        "operator_signature": normalized["operator_signature"],
        "reason": normalized["reason"],
        "signed_at": normalized["signed_at"],
        "source_review_sha256": review["paper_operator_review_package_sha256"],
    }
    signature_evidence_sha256 = sha256_of(signed_payload)
    ledger = [
        {"ledger_index": 1, "event": "OPERATOR_REVIEW_PACKAGE_VERIFIED", "state": "PASS", "decision_id": decision_id},
        {"ledger_index": 2, "event": "OPERATOR_CHECKLIST_CONFIRMED", "state": "PASS", "decision_id": decision_id},
        {"ledger_index": 3, "event": "OPERATOR_SIGNATURE_RECORDED", "state": "RECORDED", "decision_id": decision_id},
        {"ledger_index": 4, "event": "OPERATOR_DECISION_RECORDED", "state": selected, "decision_id": decision_id},
        {"ledger_index": 5, "event": "LIVE_TRADING_LOCK_RECONFIRMED", "state": "ENFORCED", "decision_id": decision_id},
        {"ledger_index": 6, "event": "PAPER_ACTIVATION_GATE_EVALUATED", "state": next_state, "decision_id": decision_id},
    ]
    result = {
        "status": "PASS",
        "decision": "paper_operator_decision_recorded",
        "decision_id": decision_id,
        "decision_state": decision_state,
        "next_state": next_state,
        "selected_decision": selected,
        "review_id": review["review_id"],
        "preflight_id": review["preflight_id"],
        "bundle_id": review["bundle_id"],
        "session_id": review["session_id"],
        "champion_candidate_id": review["champion_candidate_id"],
        "operator_record": {
            "operator_name": normalized["operator_name"],
            "operator_signature": normalized["operator_signature"],
            "reason": normalized["reason"],
            "signed_at": normalized["signed_at"],
            "signature_verified": True,
            "signature_evidence_sha256": signature_evidence_sha256,
        },
        "confirmed_checklist": normalized["checklist_confirmations"],
        "decision_ledger": ledger,
        "confirmed_checklist_sha256": sha256_of(normalized["checklist_confirmations"]),
        "decision_ledger_sha256": sha256_of(ledger),
        "source_paper_operator_review_package_sha256": review["paper_operator_review_package_sha256"],
        "activation_gate": {
            "paper_activation_preparation_allowed": preparation_allowed,
            "activation_allowed": False,
            "live_activation_allowed": False,
            "operator_decision_recorded": True,
            "operator_signature_verified": True,
            "next_version": "75.2F" if selected == "APPROVE_PAPER" else None,
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
    result["paper_operator_decision_record_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "paper_operator_decision_record_v75_2e.json": result,
        "paper_operator_confirmed_checklist_v75_2e.json": {
            "decision_id": result["decision_id"],
            "confirmed_checklist": result["confirmed_checklist"],
            "confirmed_checklist_sha256": result["confirmed_checklist_sha256"],
        },
        "paper_operator_decision_ledger_v75_2e.json": {
            "decision_id": result["decision_id"],
            "decision_ledger": result["decision_ledger"],
            "decision_ledger_sha256": result["decision_ledger_sha256"],
        },
    }
    for filename, data in payloads.items():
        (output_dir / filename).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "paper_operator_decision_record_v75_2e.sha256").write_text(result["paper_operator_decision_record_sha256"] + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V75.2E Paper Operator Decision Recorder")
    p.add_argument("--input", required=True, help="V75.2D review package JSON")
    p.add_argument("--decision-input", required=True, help="Human-completed decision input JSON")
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = build_decision_record(read_json(Path(args.input)), read_json(Path(args.decision_input)), read_json(Path(args.config)))
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "decision_id": result["decision_id"],
            "selected_decision": result["selected_decision"],
            "decision_state": result["decision_state"],
            "next_state": result["next_state"],
            "session_id": result["session_id"],
            "paper_activation_preparation_allowed": result["activation_gate"]["paper_activation_preparation_allowed"],
            "activation_allowed": result["activation_gate"]["activation_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "paper_operator_decision_record_sha256": result["paper_operator_decision_record_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (PaperOperatorDecisionError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "decision": "paper_operator_decision_record_failed", "error": str(exc), "approved_for_live": False, "network_used": False, "version": VERSION}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
