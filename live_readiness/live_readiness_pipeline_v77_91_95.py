from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
    }

def build_live_readiness_audit_engine(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json, (certificate_path, config_path))
    errors = []
    if cert.get("stage") != "V77.90" or cert.get("status") != "PASS":
        errors.append("risk_stress_certificate")
    if cert.get("certification_scope") != "LIVE_READINESS_AUDIT_ELIGIBILITY_ONLY":
        errors.append("certificate_scope")
    champion = cert.get("champion_candidate")
    if not champion or not champion.get("candidate_id"):
        errors.append("champion_candidate")
    required_sections = ("operational_controls","recovery_controls","security_controls","deployment_controls")
    for section in required_sections:
        if not isinstance(config.get(section), dict):
            errors.append(f"config_{section}")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.91.live_readiness_audit_engine.1",
        "stage":"V77.91","status":status,
        "audit_scope":"BROKER_INTEGRATION_READINESS_ONLY",
        "champion_candidate":champion,
        "risk_stress_summary":cert.get("risk_stress_summary",{}),
        "control_config":{k:config.get(k,{}) for k in required_sections},
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_92_OPERATIONAL_SAFETY_CHECKLIST",
    }
    doc["audit_engine_sha256"] = digest_json({k:v for k,v in doc.items() if k!="audit_engine_sha256"})
    write_json(output_dir/"live_readiness_audit_engine_v77_91.json", doc)
    ver = {
        "stage":"V77.91","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "champion_candidate_id":champion.get("candidate_id") if champion else None,
        "audit_engine_sha256":doc["audit_engine_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"live_readiness_audit_engine_verification_v77_91.json", ver)
    return doc

def build_operational_safety_checklist(engine_path: Path, output_dir: Path) -> dict:
    engine = load_json(engine_path)
    errors = []
    if engine.get("stage")!="V77.91" or engine.get("status")!="PASS":
        errors.append("engine_input")
    cfg = engine.get("control_config",{})
    op = cfg.get("operational_controls",{})
    sec = cfg.get("security_controls",{})
    dep = cfg.get("deployment_controls",{})
    checks = {
        "kill_switch_defined":bool(op.get("kill_switch_defined")),
        "max_position_limit_defined":bool(op.get("max_position_limit_defined")),
        "max_daily_loss_limit_defined":bool(op.get("max_daily_loss_limit_defined")),
        "order_rate_limit_defined":bool(op.get("order_rate_limit_defined")),
        "audit_logging_enabled":bool(op.get("audit_logging_enabled")),
        "manual_override_required":bool(op.get("manual_override_required")),
        "secrets_externalized":bool(sec.get("secrets_externalized")),
        "credentials_not_in_repository":bool(sec.get("credentials_not_in_repository")),
        "network_default_deny":bool(sec.get("network_default_deny")),
        "paper_mode_default":bool(dep.get("paper_mode_default")),
        "live_mode_default_disabled":bool(dep.get("live_mode_default_disabled")),
        "broker_adapter_not_enabled":bool(dep.get("broker_adapter_not_enabled")),
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("operational_safety_checklist")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.92.operational_safety_checklist.1",
        "stage":"V77.92","status":status,
        "checks":checks,"failed_checks":failed,
        "check_count":len(checks),
        "passed_check_count":sum(checks.values()),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_93_RECOVERY_KILL_SWITCH_AUDIT",
    }
    doc["operational_checklist_sha256"] = digest_json({k:v for k,v in doc.items() if k!="operational_checklist_sha256"})
    write_json(output_dir/"operational_safety_checklist_v77_92.json", doc)
    ver = {
        "stage":"V77.92","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "operational_checklist_sha256":doc["operational_checklist_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"operational_safety_checklist_verification_v77_92.json", ver)
    return doc

def run_recovery_kill_switch_audit(engine_path: Path, output_dir: Path) -> dict:
    engine = load_json(engine_path)
    errors = []
    if engine.get("stage")!="V77.91" or engine.get("status")!="PASS":
        errors.append("engine_input")
    cfg = engine.get("control_config",{})
    rec = cfg.get("recovery_controls",{})
    op = cfg.get("operational_controls",{})
    scenarios = [
        {"scenario_id":"R01","name":"Process Crash","required_action":"RESTORE_LAST_CHECKPOINT",
         "passed":bool(rec.get("checkpoint_restore_supported"))},
        {"scenario_id":"R02","name":"State Corruption","required_action":"BLOCK_AND_REPLAY",
         "passed":bool(rec.get("corruption_detection_supported")) and bool(rec.get("replay_supported"))},
        {"scenario_id":"R03","name":"Duplicate Order Risk","required_action":"REJECT_DUPLICATE",
         "passed":bool(rec.get("idempotency_guard_supported"))},
        {"scenario_id":"R04","name":"Broker Disconnect","required_action":"HALT_NEW_ORDERS",
         "passed":bool(op.get("kill_switch_defined")) and bool(rec.get("disconnect_halt_supported"))},
        {"scenario_id":"R05","name":"Risk Limit Breach","required_action":"ACTIVATE_KILL_SWITCH",
         "passed":bool(op.get("kill_switch_defined")) and bool(rec.get("risk_breach_kill_supported"))},
        {"scenario_id":"R06","name":"Manual Emergency Stop","required_action":"ACTIVATE_KILL_SWITCH",
         "passed":bool(op.get("manual_override_required")) and bool(rec.get("manual_stop_supported"))},
    ]
    failed = [x["scenario_id"] for x in scenarios if not x["passed"]]
    if failed:
        errors.append("recovery_kill_switch_audit")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.93.recovery_kill_switch_audit.1",
        "stage":"V77.93","status":status,
        "scenarios":scenarios,
        "scenario_count":len(scenarios),
        "passed_scenario_count":sum(x["passed"] for x in scenarios),
        "failed_scenario_ids":failed,
        "kill_switch_live_connected":False,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_94_LIVE_READINESS_SAFETY_GATE",
    }
    doc["recovery_audit_sha256"] = digest_json({k:v for k,v in doc.items() if k!="recovery_audit_sha256"})
    write_json(output_dir/"recovery_kill_switch_audit_v77_93.json", doc)
    ver = {
        "stage":"V77.93","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_scenario_ids":failed,
        "recovery_audit_sha256":doc["recovery_audit_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"recovery_kill_switch_audit_verification_v77_93.json", ver)
    return doc

def run_live_readiness_safety_gate(checklist_path: Path, recovery_path: Path, engine_path: Path, output_dir: Path) -> dict:
    checklist, recovery, engine = map(load_json,(checklist_path,recovery_path,engine_path))
    errors = []
    if checklist.get("stage")!="V77.92" or checklist.get("status")!="PASS":
        errors.append("checklist_input")
    if recovery.get("stage")!="V77.93" or recovery.get("status")!="PASS":
        errors.append("recovery_input")
    controls = engine.get("control_config",{})
    dep = controls.get("deployment_controls",{})
    checks = {
        "all_operational_checks_passed":checklist.get("failed_checks")==[],
        "all_recovery_scenarios_passed":recovery.get("failed_scenario_ids")==[],
        "paper_mode_default":bool(dep.get("paper_mode_default")),
        "live_mode_default_disabled":bool(dep.get("live_mode_default_disabled")),
        "broker_adapter_not_enabled":bool(dep.get("broker_adapter_not_enabled")),
        "actual_orders_zero":engine.get("actual_orders_submitted")==0,
        "network_disabled":engine.get("network_allowed") is False,
        "broker_disconnected":engine.get("broker_connected") is False,
        "live_trading_unauthorized":engine.get("live_trading_authorized") is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("live_readiness_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.94.live_readiness_safety_gate.1",
        "stage":"V77.94","status":status,
        "gate_scope":"BROKER_INTEGRATION_SKELETON_ELIGIBILITY_ONLY",
        "decision":"ALLOW_BROKER_INTEGRATION_SKELETON" if not errors else "BLOCK_BROKER_INTEGRATION_SKELETON",
        "live_trading_approved":False,
        "broker_connection_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_95_LIVE_READINESS_CERTIFICATE",
    }
    doc["live_readiness_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="live_readiness_gate_sha256"})
    write_json(output_dir/"live_readiness_safety_gate_v77_94.json", doc)
    ver = {
        "stage":"V77.94","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "live_readiness_gate_sha256":doc["live_readiness_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"live_readiness_safety_gate_verification_v77_94.json", ver)
    return doc

def issue_live_readiness_certificate(v91: Path,v92: Path,v93: Path,v94: Path,engine_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v91,v92,v93,v94)))
    engine = load_json(engine_path)
    expected = ["V77.91","V77.92","V77.93","V77.94"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    champion = engine.get("champion_candidate")
    if not champion:
        errors.append("champion")
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v77.95.live_readiness_certificate.1",
        "stage":"V77.95",
        "certificate_id":"LIVE-READINESS-AUDIT-V77.95",
        "status":status,
        "decision":"certified_for_broker_integration_skeleton" if not errors else "live_readiness_rejected",
        "certification_scope":"BROKER_INTEGRATION_SKELETON_ELIGIBILITY_ONLY",
        "live_trading_approved":False,
        "broker_connection_approved":False,
        "real_credentials_allowed":False,
        "actual_order_submission_allowed":False,
        "certified_stages":expected,
        "champion_candidate":champion,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_96_BROKER_INTEGRATION_SKELETON" if not errors else "REPAIR_V77_95",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"live_readiness_certificate_v77_95.json", cert)
    ver = {
        "stage":"V77.95","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "champion_candidate_id":champion.get("candidate_id") if champion else None,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"live_readiness_certificate_verification_v77_95.json", ver)
    return cert
