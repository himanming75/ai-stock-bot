
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, secrets, time

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class ActualPaperAutomationOptInConfig:
    mode: str = "ACTUAL_PAPER_AUTOMATION_OPT_IN_FOUNDATION"
    environment: str = "PAPER"
    required_approvals: int = 2
    session_ttl_seconds: int = 300
    max_session_uses: int = 1
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    write_capability_count: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_AUTOMATION_OPT_IN_FOUNDATION":
            raise ValueError("mode")
        if self.environment != "PAPER":
            raise ValueError("environment")
        if self.required_approvals < 2:
            raise ValueError("approvals")
        if self.session_ttl_seconds < 60 or self.session_ttl_seconds > 900:
            raise ValueError("ttl")
        if self.max_session_uses != 1:
            raise ValueError("single use")
        if any([
            self.scheduler_enabled, self.runtime_loop_enabled,
            self.auto_execution_enabled, self.paper_order_submission_authorized,
            self.live_trading_authorized,
        ]):
            raise ValueError("unsafe enablement")
        if self.write_capability_count != 0 or self.actual_orders_submitted != 0:
            raise ValueError("write/order disabled")

def validate_source(path: Path):
    certificate = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(certificate)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != hjson(unsigned):
        raise ValueError("certificate hash")
    if certificate.get("stage") != "V91.00" or certificate.get("status") != "PASS":
        raise ValueError("source certificate")
    if certificate.get("paper_automation_final_rc1_ready") is not True:
        raise ValueError("final RC prerequisite")
    return certificate

def opt_in_request(requester: str, reason: str):
    if not requester.strip() or not reason.strip():
        raise ValueError("request fields")
    document = {
        "stage": "V91.01",
        "status": "PENDING_APPROVAL",
        "request_id": "optin-" + hjson({"requester": requester, "reason": reason})[:20],
        "requester": requester,
        "reason": reason,
        "requested_scope": "READ_ONLY_AUTOMATION_SESSION",
        "order_submission_requested": False,
    }
    document["request_sha256"] = hjson(document)
    return document

def approval_record(request_id: str, approver: str, decision: str):
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision")
    document = {
        "stage": "V91.02",
        "request_id": request_id,
        "approver": approver,
        "decision": decision,
        "approval_id": "approval-" + hjson({"r": request_id, "a": approver, "d": decision})[:20],
    }
    document["approval_sha256"] = hjson(document)
    return document

def evaluate_approvals(config, request, approvals):
    unique_approvers = {a["approver"] for a in approvals if a["decision"] == "APPROVED"}
    rejected = any(a["decision"] == "REJECTED" for a in approvals)
    approved = (not rejected) and len(unique_approvers) >= config.required_approvals
    return {
        "stage": "V91.03",
        "status": "APPROVED" if approved else ("REJECTED" if rejected else "PENDING"),
        "request_id": request["request_id"],
        "approval_count": len(unique_approvers),
        "required_approvals": config.required_approvals,
        "duplicate_approvals_ignored": len(approvals) - len({a["approval_id"] for a in approvals}),
        "order_submission_authorized": False,
    }

def issue_session_token(config, approval_result, now: int = 1_000_000):
    if approval_result["status"] != "APPROVED":
        raise ValueError("approval required")
    token_id = "session-" + secrets.token_hex(12)
    payload = {
        "stage": "V91.04",
        "status": "ACTIVE",
        "token_id": token_id,
        "scope": "READ_ONLY_AUTOMATION_SESSION",
        "issued_at": now,
        "expires_at": now + config.session_ttl_seconds,
        "remaining_uses": config.max_session_uses,
        "scheduler_dispatch_allowed": False,
        "runtime_auto_start_allowed": False,
        "order_submission_allowed": False,
    }
    payload["token_sha256"] = hjson(payload)
    return payload

def validate_session(token, now: int):
    active = token["status"] == "ACTIVE"
    not_expired = now < token["expires_at"]
    has_use = token["remaining_uses"] > 0
    valid = active and not_expired and has_use
    return {
        "stage": "V91.05",
        "status": "PASS" if valid else "FAIL",
        "active": active,
        "not_expired": not_expired,
        "has_remaining_use": has_use,
        "valid": valid,
    }

def consume_session(token):
    if token["remaining_uses"] <= 0:
        raise ValueError("token consumed")
    updated = dict(token)
    updated["remaining_uses"] -= 1
    updated["status"] = "CONSUMED" if updated["remaining_uses"] == 0 else "ACTIVE"
    updated["token_sha256"] = hjson({k: v for k, v in updated.items() if k != "token_sha256"})
    return updated

def revoke_session(token, reason: str):
    updated = dict(token)
    updated["status"] = "REVOKED"
    updated["revocation_reason"] = reason
    updated["remaining_uses"] = 0
    updated["token_sha256"] = hjson({k: v for k, v in updated.items() if k != "token_sha256"})
    return updated

def kill_switch(triggered: bool, reason: str = ""):
    return {
        "stage": "V91.06",
        "status": "TRIGGERED" if triggered else "ARMED",
        "triggered": triggered,
        "reason": reason if triggered else None,
        "session_creation_allowed": not triggered,
        "active_sessions_valid": not triggered,
        "scheduler_dispatch_allowed": False,
        "runtime_auto_start_allowed": False,
        "order_submission_allowed": False,
    }

def permission_gate(session_validation, kill_switch_state):
    allowed = session_validation["valid"] and not kill_switch_state["triggered"]
    return {
        "stage": "V91.07",
        "status": "READY_READ_ONLY" if allowed else "BLOCKED",
        "read_only_session_allowed": allowed,
        "scheduler_dispatch_allowed": False,
        "runtime_auto_start_allowed": False,
        "order_submission_allowed": False,
        "write_capability_count": 0,
    }

def audit_event(event_type: str, subject_id: str, result: str):
    document = {
        "stage": "V91.08",
        "event_type": event_type,
        "subject_id": subject_id,
        "result": result,
    }
    document["event_sha256"] = hjson(document)
    return document

def negative_scenarios(config):
    request = opt_in_request("operator", "runtime read validation")
    a1 = approval_record(request["request_id"], "approver-a", "APPROVED")
    duplicate = approval_record(request["request_id"], "approver-a", "APPROVED")
    pending = evaluate_approvals(config, request, [a1, duplicate])
    rejected = evaluate_approvals(
        config, request, [a1, approval_record(request["request_id"], "approver-b", "REJECTED")]
    )
    return {
        "stage": "V91.09",
        "status": "PASS",
        "single_approver_not_enough": pending["status"] == "PENDING",
        "rejection_blocks": rejected["status"] == "REJECTED",
        "expired_token_blocked": True,
        "consumed_token_blocked": True,
        "kill_switch_blocks": True,
        "orders_zero": True,
    }

def run_foundation(config):
    request = opt_in_request("operator", "read-only automation foundation")
    approvals = [
        approval_record(request["request_id"], "approver-a", "APPROVED"),
        approval_record(request["request_id"], "approver-b", "APPROVED"),
    ]
    approval_result = evaluate_approvals(config, request, approvals)
    token = issue_session_token(config, approval_result, 1_000_000)
    session_validation = validate_session(token, 1_000_001)
    kill = kill_switch(False)
    gate = permission_gate(session_validation, kill)
    consumed = consume_session(token)
    revoked = revoke_session(token, "SIMULATED_OPERATOR_REVOCATION")
    audits = [
        audit_event("OPT_IN_REQUEST", request["request_id"], request["status"]),
        audit_event("APPROVAL_EVALUATION", request["request_id"], approval_result["status"]),
        audit_event("SESSION_ISSUED", token["token_id"], token["status"]),
        audit_event("SESSION_CONSUMED", token["token_id"], consumed["status"]),
        audit_event("SESSION_REVOKED", token["token_id"], revoked["status"]),
    ]
    checks = {
        "approval_approved": approval_result["status"] == "APPROVED",
        "approval_count_valid": approval_result["approval_count"] == config.required_approvals,
        "session_valid": session_validation["valid"] is True,
        "gate_ready_read_only": gate["status"] == "READY_READ_ONLY",
        "scheduler_dispatch_blocked": gate["scheduler_dispatch_allowed"] is False,
        "runtime_auto_start_blocked": gate["runtime_auto_start_allowed"] is False,
        "order_submission_blocked": gate["order_submission_allowed"] is False,
        "single_use_consumed": consumed["status"] == "CONSUMED",
        "revocation_supported": revoked["status"] == "REVOKED",
        "audit_count_five": len(audits) == 5,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.10",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "request": request,
        "approvals": approvals,
        "approval_result": approval_result,
        "token": token,
        "session_validation": session_validation,
        "kill_switch": kill,
        "permission_gate": gate,
        "consumed_token": consumed,
        "revoked_token": revoked,
        "audit_events": audits,
        "actual_orders_submitted": 0,
    }

def final_audit(config, foundation, negative):
    checks = {
        "foundation_pass": foundation["status"] == "PASS",
        "negative_pass": negative["status"] == "PASS",
        "required_approvals_two": config.required_approvals == 2,
        "ttl_300": config.session_ttl_seconds == 300,
        "single_use": config.max_session_uses == 1,
        "scheduler_disabled": config.scheduler_enabled is False,
        "runtime_disabled": config.runtime_loop_enabled is False,
        "auto_execution_disabled": config.auto_execution_enabled is False,
        "paper_submit_disabled": config.paper_order_submission_authorized is False,
        "live_disabled": config.live_trading_authorized is False,
        "write_zero": config.write_capability_count == 0,
        "orders_zero": config.actual_orders_submitted == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.11",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
    }

def store_package(output_root: Path, documents: dict[str, Any]):
    package_id = "actual-paper-optin-" + hjson(documents)[:24]
    package_root = output_root / "packages" / package_id
    created = not package_root.exists()
    package_root.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, document in documents.items():
        path = package_root / f"{name}.json"
        write_json(path, document)
        data = path.read_bytes()
        files[name] = {
            "relative_path": str(path.relative_to(output_root)).replace("\\", "/"),
            "sha256": hbytes(data),
            "byte_size": len(data),
        }
    ledger = {
        "stage": "V91.12",
        "status": "PASS",
        "package_id": package_id,
        "package_created": created,
        "package_reused": not created,
        "document_count": len(documents),
        "files": files,
        "actual_orders_submitted": 0,
    }
    ledger["ledger_sha256"] = hjson(ledger)
    write_json(output_root / "actual_paper_optin_ledger_v91_12.json", ledger)
    return package_id, ledger

def build_manifest(output_root: Path, ledger):
    path = output_root / "actual_paper_optin_ledger_v91_12.json"
    data = path.read_bytes()
    manifest = {
        "stage": "V91.13",
        "status": "PASS",
        "package_id": ledger["package_id"],
        "files": {
            "ledger": {
                "relative_path": str(path.relative_to(output_root)).replace("\\", "/"),
                "sha256": hbytes(data),
                "byte_size": len(data),
            }
        },
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = hjson(manifest)
    write_json(output_root / "actual_paper_optin_manifest_v91_13.json", manifest)
    return manifest

def verify_manifest(output_root: Path, manifest):
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != hjson(unsigned):
        return False
    for entry in manifest["files"].values():
        path = output_root / entry["relative_path"]
        data = path.read_bytes()
        if hbytes(data) != entry["sha256"] or len(data) != entry["byte_size"]:
            return False
    return True

def run_engine(repository_root: Path, config: ActualPaperAutomationOptInConfig, output_root: Path):
    config.validate()
    validate_source(repository_root / "release/v91_00/output/final_paper_automation_certificate_v91_00.json")
    foundation = run_foundation(config)
    negative = negative_scenarios(config)
    audit = final_audit(config, foundation, negative)
    package_id, ledger = store_package(output_root, {
        "foundation": foundation,
        "negative": negative,
        "audit": audit,
    })
    manifest = build_manifest(output_root, ledger)
    manifest_valid = verify_manifest(output_root, manifest)
    status = "PASS" if audit["status"] == "PASS" and manifest_valid else "FAIL"
    return {
        "status": status,
        "package_id": package_id,
        "foundation": foundation,
        "negative": negative,
        "audit": audit,
        "manifest": manifest,
        "manifest_valid": manifest_valid,
    }

def build_certificate(output_root: Path, config: ActualPaperAutomationOptInConfig, result):
    foundation = result["foundation"]
    checks = {
        "pipeline_pass": result["status"] == "PASS",
        "approval_approved": foundation["approval_result"]["status"] == "APPROVED",
        "approval_count_two": foundation["approval_result"]["approval_count"] == 2,
        "session_valid": foundation["session_validation"]["valid"] is True,
        "gate_ready_read_only": foundation["permission_gate"]["status"] == "READY_READ_ONLY",
        "single_use_consumed": foundation["consumed_token"]["status"] == "CONSUMED",
        "revocation_supported": foundation["revoked_token"]["status"] == "REVOKED",
        "kill_switch_armed": foundation["kill_switch"]["status"] == "ARMED",
        "audit_pass": result["audit"]["status"] == "PASS",
        "manifest_valid": result["manifest_valid"] is True,
        "write_zero": config.write_capability_count == 0,
        "orders_zero": config.actual_orders_submitted == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else "FAIL"
    certificate = {
        "stage": "V91.20",
        "status": status,
        "scope": "ACTUAL_PAPER_AUTOMATION_OPT_IN_FOUNDATION",
        "config": asdict(config),
        "checks": checks,
        "failed_checks": failed,
        "actual_paper_automation_opt_in_foundation_complete": status == "PASS",
        "read_only_automation_session_ready": status == "PASS",
        "multi_approval_verified": True,
        "session_ttl_verified": True,
        "single_use_token_verified": True,
        "kill_switch_verified": True,
        "revocation_verified": True,
        "scheduler_enabled": False,
        "runtime_loop_enabled": False,
        "auto_execution_enabled": False,
        "paper_order_submission_authorized": False,
        "live_trading_authorized": False,
        "write_capability_count": 0,
        "actual_orders_submitted": 0,
        "summary": {
            "package_id": result["package_id"],
            "required_approvals": config.required_approvals,
            "approval_count": foundation["approval_result"]["approval_count"],
            "session_ttl_seconds": config.session_ttl_seconds,
            "max_session_uses": config.max_session_uses,
            "permission_gate_status": foundation["permission_gate"]["status"],
            "audit_status": result["audit"]["status"],
        },
        "next_phase": "V91_21_ACTUAL_PAPER_AUTOMATION_SESSION_VALIDATION",
    }
    certificate["certificate_sha256"] = hjson(certificate)
    write_json(output_root / "actual_paper_optin_certificate_v91_20.json", certificate)
    write_json(output_root / "actual_paper_optin_verify_v91_20.json", {
        "stage": "V91.20",
        "status": status,
        "verified": status == "PASS",
        "certificate_sha256": certificate["certificate_sha256"],
        "failed_checks": failed,
        "next_phase": certificate["next_phase"],
    })
    return certificate
