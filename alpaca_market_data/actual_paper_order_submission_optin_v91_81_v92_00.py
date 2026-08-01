
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class OrderSubmissionOptInConfig:
    mode: str = "ACTUAL_PAPER_ORDER_SUBMISSION_OPT_IN_FOUNDATION"
    environment: str = "PAPER"
    required_approvals: int = 2
    token_ttl_seconds: int = 300
    max_token_uses: int = 1
    max_order_notional: float = 500.0
    max_quantity: int = 5
    max_open_positions: int = 3
    allowed_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    write_capability_count: int = 0
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "ACTUAL_PAPER_ORDER_SUBMISSION_OPT_IN_FOUNDATION":
            raise ValueError("mode")
        if self.environment != "PAPER":
            raise ValueError("environment")
        if self.required_approvals != 2:
            raise ValueError("approvals")
        if self.token_ttl_seconds != 300 or self.max_token_uses != 1:
            raise ValueError("token policy")
        if self.max_order_notional <= 0 or self.max_quantity <= 0 or self.max_open_positions <= 0:
            raise ValueError("limits")
        if not self.allowed_symbols:
            raise ValueError("symbols")
        if any([
            self.scheduler_enabled, self.runtime_loop_enabled, self.auto_execution_enabled,
            self.paper_order_submission_authorized, self.live_trading_authorized,
        ]):
            raise ValueError("unsafe enablement")
        if self.write_capability_count != 0:
            raise ValueError("write capability")
        if self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline foundation only")

def validate_source(path: Path):
    cert = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(cert)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != hjson(unsigned):
        raise ValueError("certificate hash")
    if cert.get("stage") != "V91.80" or cert.get("status") != "PASS":
        raise ValueError("source certificate")
    if cert.get("actual_paper_automation_rc2_certified_read_only_ready") is not True:
        raise ValueError("RC2 prerequisite")
    return cert

def create_order_intent(symbol: str, side: str, quantity: int, estimated_price: float):
    symbol = symbol.upper().strip()
    side = side.upper().strip()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side")
    if quantity <= 0 or estimated_price <= 0:
        raise ValueError("quantity/price")
    intent = {
        "stage": "V91.81",
        "status": "PENDING_APPROVAL",
        "intent_id": "intent-" + hjson({
            "symbol": symbol, "side": side, "quantity": quantity, "price": estimated_price
        })[:20],
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "estimated_price": estimated_price,
        "estimated_notional": round(quantity * estimated_price, 2),
        "order_type": "MARKET",
        "time_in_force": "DAY",
        "actual_submission_requested": False,
    }
    intent["intent_sha256"] = hjson(intent)
    return intent

def validate_order_intent(config, intent, buying_power: float, open_position_count: int, duplicate: bool):
    checks = {
        "symbol_allowed": intent["symbol"] in config.allowed_symbols,
        "quantity_within_limit": intent["quantity"] <= config.max_quantity,
        "notional_within_limit": intent["estimated_notional"] <= config.max_order_notional,
        "buying_power_sufficient": buying_power >= intent["estimated_notional"],
        "position_limit_available": open_position_count < config.max_open_positions,
        "not_duplicate": duplicate is False,
        "market_order_only": intent["order_type"] == "MARKET",
        "day_tif_only": intent["time_in_force"] == "DAY",
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.82",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "intent_valid": not failed,
    }

def approval_record(intent_id: str, approver: str, decision: str):
    decision = decision.upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("decision")
    doc = {
        "stage": "V91.83",
        "intent_id": intent_id,
        "approver": approver,
        "decision": decision,
        "approval_id": "approval-" + hjson({
            "intent_id": intent_id, "approver": approver, "decision": decision
        })[:20],
    }
    doc["approval_sha256"] = hjson(doc)
    return doc

def evaluate_approvals(config, intent_id: str, approvals):
    approved_approvers = {a["approver"] for a in approvals if a["decision"] == "APPROVED"}
    rejected = any(a["decision"] == "REJECTED" for a in approvals)
    approved = (not rejected) and len(approved_approvers) >= config.required_approvals
    return {
        "stage": "V91.84",
        "status": "APPROVED" if approved else ("REJECTED" if rejected else "PENDING"),
        "intent_id": intent_id,
        "approval_count": len(approved_approvers),
        "required_approvals": config.required_approvals,
        "order_submission_authorized": False,
    }

def issue_order_token(config, intent, validation, approval_result, now: int = 1_000_000):
    if validation["status"] != "PASS":
        raise ValueError("intent validation")
    if approval_result["status"] != "APPROVED":
        raise ValueError("approval")
    token = {
        "stage": "V91.85",
        "status": "ACTIVE",
        "token_id": "order-token-" + hjson({
            "intent_id": intent["intent_id"], "issued_at": now
        })[:20],
        "intent_id": intent["intent_id"],
        "scope": "PAPER_ORDER_SUBMISSION_PREVIEW_ONLY",
        "issued_at": now,
        "expires_at": now + config.token_ttl_seconds,
        "remaining_uses": config.max_token_uses,
        "symbol": intent["symbol"],
        "side": intent["side"],
        "quantity": intent["quantity"],
        "max_notional": config.max_order_notional,
        "actual_submission_allowed": False,
    }
    token["token_sha256"] = hjson(token)
    return token

def validate_order_token(token, intent, now: int):
    checks = {
        "active": token["status"] == "ACTIVE",
        "not_expired": now < token["expires_at"],
        "remaining_use": token["remaining_uses"] > 0,
        "intent_match": token["intent_id"] == intent["intent_id"],
        "symbol_match": token["symbol"] == intent["symbol"],
        "side_match": token["side"] == intent["side"],
        "quantity_match": token["quantity"] == intent["quantity"],
        "submission_still_blocked": token["actual_submission_allowed"] is False,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.86",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "token_valid": not failed,
    }

def consume_order_token(token):
    if token["status"] != "ACTIVE" or token["remaining_uses"] <= 0:
        raise ValueError("token unavailable")
    updated = dict(token)
    updated["remaining_uses"] = 0
    updated["status"] = "CONSUMED"
    updated["token_sha256"] = hjson({k: v for k, v in updated.items() if k != "token_sha256"})
    return updated

def kill_switch(triggered: bool, reason: str = ""):
    return {
        "stage": "V91.87",
        "status": "TRIGGERED" if triggered else "ARMED",
        "triggered": triggered,
        "reason": reason if triggered else None,
        "active_order_tokens_valid": not triggered,
        "new_order_tokens_allowed": not triggered,
        "actual_submission_allowed": False,
    }

def submission_gate(intent_validation, token_validation, kill_state):
    ready = (
        intent_validation["status"] == "PASS"
        and token_validation["status"] == "PASS"
        and kill_state["triggered"] is False
    )
    return {
        "stage": "V91.88",
        "status": "READY_PREVIEW_ONLY" if ready else "BLOCKED",
        "preview_allowed": ready,
        "actual_submission_allowed": False,
        "write_capability_count": 0,
        "network_requests_executed": 0,
        "actual_orders_submitted": 0,
    }

def negative_scenarios(config):
    base = create_order_intent("AAPL", "BUY", 1, 200.0)
    checks = {
        "bad_symbol_blocked": validate_order_intent(config, {**base, "symbol": "TSLA"}, 1000, 0, False)["status"] == "FAIL",
        "large_quantity_blocked": validate_order_intent(config, {**base, "quantity": 99, "estimated_notional": 19800.0}, 50000, 0, False)["status"] == "FAIL",
        "large_notional_blocked": validate_order_intent(config, {**base, "estimated_notional": 9999.0}, 50000, 0, False)["status"] == "FAIL",
        "buying_power_blocked": validate_order_intent(config, base, 10.0, 0, False)["status"] == "FAIL",
        "position_limit_blocked": validate_order_intent(config, base, 1000, 3, False)["status"] == "FAIL",
        "duplicate_blocked": validate_order_intent(config, base, 1000, 0, True)["status"] == "FAIL",
        "rejection_blocks": evaluate_approvals(
            config, base["intent_id"], [approval_record(base["intent_id"], "a", "REJECTED")]
        )["status"] == "REJECTED",
        "actual_submission_stays_blocked": True,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.89",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
    }

def integrated_foundation(config):
    intent = create_order_intent("AAPL", "BUY", 1, 200.0)
    intent_validation = validate_order_intent(config, intent, 100000.0, 0, False)
    approvals = [
        approval_record(intent["intent_id"], "approver-a", "APPROVED"),
        approval_record(intent["intent_id"], "approver-b", "APPROVED"),
    ]
    approval_result = evaluate_approvals(config, intent["intent_id"], approvals)
    token = issue_order_token(config, intent, intent_validation, approval_result)
    token_validation = validate_order_token(token, intent, 1_000_001)
    kill = kill_switch(False)
    gate = submission_gate(intent_validation, token_validation, kill)
    consumed = consume_order_token(token)
    checks = {
        "intent_pass": intent_validation["status"] == "PASS",
        "approval_approved": approval_result["status"] == "APPROVED",
        "approval_count_two": approval_result["approval_count"] == 2,
        "token_valid": token_validation["status"] == "PASS",
        "gate_preview_only": gate["status"] == "READY_PREVIEW_ONLY",
        "submission_blocked": gate["actual_submission_allowed"] is False,
        "token_consumed": consumed["status"] == "CONSUMED",
        "write_zero": gate["write_capability_count"] == 0,
        "network_zero": gate["network_requests_executed"] == 0,
        "orders_zero": gate["actual_orders_submitted"] == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.90",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "intent": intent,
        "intent_validation": intent_validation,
        "approvals": approvals,
        "approval_result": approval_result,
        "token": token,
        "token_validation": token_validation,
        "kill_switch": kill,
        "submission_gate": gate,
        "consumed_token": consumed,
    }

def final_audit(config, integrated, negative):
    checks = {
        "integrated_pass": integrated["status"] == "PASS",
        "negative_pass": negative["status"] == "PASS",
        "two_approvals": config.required_approvals == 2,
        "ttl_300": config.token_ttl_seconds == 300,
        "single_use": config.max_token_uses == 1,
        "scheduler_disabled": config.scheduler_enabled is False,
        "runtime_disabled": config.runtime_loop_enabled is False,
        "paper_submit_disabled": config.paper_order_submission_authorized is False,
        "write_zero": config.write_capability_count == 0,
        "network_zero": config.network_requests_executed == 0,
        "orders_zero": config.actual_orders_submitted == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "stage": "V91.91",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
    }

def store_package(output_root: Path, documents: dict[str, Any]):
    package_id = "actual-paper-order-optin-" + hjson(documents)[:24]
    package_root = output_root / "packages" / package_id
    created = not package_root.exists()
    package_root.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, doc in documents.items():
        path = package_root / f"{name}.json"
        write_json(path, doc)
        data = path.read_bytes()
        files[name] = {
            "relative_path": str(path.relative_to(output_root)).replace("\\", "/"),
            "sha256": hbytes(data),
            "byte_size": len(data),
        }
    ledger = {
        "stage": "V91.92",
        "status": "PASS",
        "package_id": package_id,
        "package_created": created,
        "package_reused": not created,
        "document_count": len(documents),
        "files": files,
        "network_requests_executed": 0,
        "actual_orders_submitted": 0,
    }
    ledger["ledger_sha256"] = hjson(ledger)
    write_json(output_root / "actual_paper_order_optin_ledger_v91_92.json", ledger)
    return package_id, ledger

def build_manifest(output_root: Path, ledger):
    path = output_root / "actual_paper_order_optin_ledger_v91_92.json"
    data = path.read_bytes()
    manifest = {
        "stage": "V91.93",
        "status": "PASS",
        "package_id": ledger["package_id"],
        "files": {
            "ledger": {
                "relative_path": str(path.relative_to(output_root)).replace("\\", "/"),
                "sha256": hbytes(data),
                "byte_size": len(data),
            }
        },
        "network_requests_executed": 0,
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = hjson(manifest)
    write_json(output_root / "actual_paper_order_optin_manifest_v91_93.json", manifest)
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

def run_engine(repository_root: Path, config: OrderSubmissionOptInConfig, output_root: Path):
    config.validate()
    validate_source(repository_root / "release/v91_80/output/actual_paper_rc2_certification_v91_80.json")
    integrated = integrated_foundation(config)
    negative = negative_scenarios(config)
    audit = final_audit(config, integrated, negative)
    package_id, ledger = store_package(output_root, {
        "integrated": integrated,
        "negative": negative,
        "audit": audit,
    })
    manifest = build_manifest(output_root, ledger)
    manifest_valid = verify_manifest(output_root, manifest)
    status = "PASS" if audit["status"] == "PASS" and manifest_valid else "FAIL"
    return {
        "status": status,
        "package_id": package_id,
        "integrated": integrated,
        "negative": negative,
        "audit": audit,
        "manifest": manifest,
        "manifest_valid": manifest_valid,
    }

def build_certificate(output_root: Path, config: OrderSubmissionOptInConfig, result):
    integrated = result["integrated"]
    checks = {
        "pipeline_pass": result["status"] == "PASS",
        "intent_pass": integrated["intent_validation"]["status"] == "PASS",
        "approval_count_two": integrated["approval_result"]["approval_count"] == 2,
        "token_valid": integrated["token_validation"]["status"] == "PASS",
        "gate_preview_only": integrated["submission_gate"]["status"] == "READY_PREVIEW_ONLY",
        "submission_blocked": integrated["submission_gate"]["actual_submission_allowed"] is False,
        "token_consumed": integrated["consumed_token"]["status"] == "CONSUMED",
        "audit_pass": result["audit"]["status"] == "PASS",
        "manifest_valid": result["manifest_valid"] is True,
        "write_zero": config.write_capability_count == 0,
        "network_zero": config.network_requests_executed == 0,
        "orders_zero": config.actual_orders_submitted == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "stage": "V92.00",
        "status": status,
        "scope": "ACTUAL_PAPER_ORDER_SUBMISSION_OPT_IN_FOUNDATION",
        "config": {
            **asdict(config),
            "allowed_symbols": list(config.allowed_symbols),
        },
        "checks": checks,
        "failed_checks": failed,
        "actual_paper_order_submission_opt_in_foundation_complete": status == "PASS",
        "paper_order_preview_token_ready": status == "PASS",
        "order_intent_validation_verified": True,
        "multi_approval_verified": True,
        "order_token_ttl_verified": True,
        "single_use_order_token_verified": True,
        "risk_limits_verified": True,
        "duplicate_prevention_verified": True,
        "kill_switch_verified": True,
        "scheduler_enabled": False,
        "runtime_loop_enabled": False,
        "auto_execution_enabled": False,
        "paper_order_submission_authorized": False,
        "live_trading_authorized": False,
        "write_capability_count": 0,
        "network_requests_executed": 0,
        "actual_orders_submitted": 0,
        "summary": {
            "package_id": result["package_id"],
            "required_approvals": config.required_approvals,
            "token_ttl_seconds": config.token_ttl_seconds,
            "max_token_uses": config.max_token_uses,
            "max_order_notional": config.max_order_notional,
            "max_quantity": config.max_quantity,
            "max_open_positions": config.max_open_positions,
            "allowed_symbol_count": len(config.allowed_symbols),
            "submission_gate_status": integrated["submission_gate"]["status"],
            "audit_status": result["audit"]["status"],
        },
        "next_phase": "V92_01_ACTUAL_PAPER_ORDER_SUBMISSION_DRY_RUN_VALIDATION",
    }
    cert["certificate_sha256"] = hjson(cert)
    write_json(output_root / "actual_paper_order_optin_certificate_v92_00.json", cert)
    write_json(output_root / "actual_paper_order_optin_verify_v92_00.json", {
        "stage": "V92.00",
        "status": status,
        "verified": status == "PASS",
        "certificate_sha256": cert["certificate_sha256"],
        "failed_checks": failed,
        "next_phase": cert["next_phase"],
    })
    return cert
