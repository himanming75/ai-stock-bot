from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

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
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class ModuleCertificateRecord:
    sequence: int
    stage: str
    certificate_path: str
    certificate_sha256: str
    certificate_status: str
    certification_scope: str
    previous_record_sha256: str
    record_sha256: str

def build_module_record(sequence:int, stage:str, certificate_path:str, certificate:dict,
                        previous_record_sha256:str)->ModuleCertificateRecord:
    source_sha=digest_json(certificate)
    base={
        "sequence":sequence,
        "stage":stage,
        "certificate_path":certificate_path.replace("\\","/"),
        "certificate_sha256":source_sha,
        "certificate_status":certificate.get("status"),
        "certification_scope":certificate.get("certification_scope"),
        "previous_record_sha256":previous_record_sha256,
    }
    return ModuleCertificateRecord(
        **base,
        record_sha256=digest_json(base)
    )

def verify_module_chain(records:list[ModuleCertificateRecord])->bool:
    previous=""
    for idx,record in enumerate(records,1):
        if record.sequence!=idx:
            raise ValueError("module sequence gap")
        if record.previous_record_sha256!=previous:
            raise ValueError("module chain mismatch")
        expected=digest_json({
            "sequence":record.sequence,
            "stage":record.stage,
            "certificate_path":record.certificate_path,
            "certificate_sha256":record.certificate_sha256,
            "certificate_status":record.certificate_status,
            "certification_scope":record.certification_scope,
            "previous_record_sha256":record.previous_record_sha256,
        })
        if expected!=record.record_sha256:
            raise ValueError("module record hash mismatch")
        previous=record.record_sha256
    return True

def build_final_system_certification_foundation(runtime_certificate_path:Path,
                                                config_path:Path,
                                                output_dir:Path)->dict:
    runtime_cert,config=map(load_json,(runtime_certificate_path,config_path))
    errors=[]
    if runtime_cert.get("stage")!="V78.90" or runtime_cert.get("status")!="PASS":
        errors.append("operation_runtime_certificate")
    if runtime_cert.get("certification_scope")!="OFFLINE_FINAL_SYSTEM_CERTIFICATION_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    final_cfg=config.get("final_system_certification",{})
    for key in ("system_id","system_version","required_certificates","allow_live_activation"):
        if key not in final_cfg:
            errors.append(f"config_{key}")
    if final_cfg.get("allow_live_activation") is not False:
        errors.append("live_activation_flag")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.91.final_system_certification_foundation.1",
        "stage":"V78.91","status":status,
        "scope":"OFFLINE_FINAL_SYSTEM_CERTIFICATION_ONLY",
        "champion_candidate":runtime_cert.get("champion_candidate"),
        "release_id":runtime_cert.get("release_id"),
        "runtime_id":runtime_cert.get("runtime_id"),
        "final_system_certification":final_cfg,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_92_CROSS_MODULE_INTEGRITY_AUDIT",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"final_system_certification_foundation_v78_91.json",doc)
    ver={"stage":"V78.91","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"final_system_certification_foundation_verification_v78_91.json",ver)
    return doc

def run_cross_module_integrity_audit(repository_root:Path,
                                     foundation_path:Path,
                                     output_dir:Path)->dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.91" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    records=[]
    previous=""
    missing=[]
    invalid=[]
    for idx,rel in enumerate(foundation.get("final_system_certification",{}).get("required_certificates",[]),1):
        path=repository_root/rel
        if not path.is_file():
            missing.append(rel)
            continue
        cert=load_json(path)
        if cert.get("status")!="PASS":
            invalid.append(rel)
        record=build_module_record(idx,cert.get("stage","UNKNOWN"),rel,cert,previous)
        records.append(record)
        previous=record.record_sha256
    try:
        chain_verified=verify_module_chain(records)
    except Exception as exc:
        chain_verified=False
        errors.append(f"module_chain_exception:{type(exc).__name__}")
    if missing:
        errors.append("missing_certificates")
    if invalid:
        errors.append("invalid_certificates")
    expected_count=len(foundation.get("final_system_certification",{}).get("required_certificates",[]))
    checks={
        "certificate_count_matches":len(records)==expected_count,
        "module_chain_verified":chain_verified,
        "all_certificates_passed":not invalid,
        "no_missing_certificates":not missing,
        "record_hashes_unique":len({x.record_sha256 for x in records})==len(records),
        "certificate_hashes_unique":len({x.certificate_sha256 for x in records})==len(records),
        "final_stage_present":any(x.stage=="V78.90" for x in records),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("cross_module_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.92.cross_module_integrity_audit.1",
        "stage":"V78.92","status":status,
        "module_certificate_records":[asdict(x) for x in records],
        "module_chain_head":records[-1].record_sha256 if records else "",
        "missing_certificates":missing,
        "invalid_certificates":invalid,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_93_END_TO_END_REPLAY_VALIDATION",
    }
    doc["integrity_audit_sha256"]=digest_json({k:v for k,v in doc.items() if k!="integrity_audit_sha256"})
    write_json(output_dir/"cross_module_integrity_audit_v78_92.json",doc)
    ver={"stage":"V78.92","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "integrity_audit_sha256":doc["integrity_audit_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"cross_module_integrity_audit_verification_v78_92.json",ver)
    return doc

def run_end_to_end_replay_validation(repository_root:Path,
                                     foundation_path:Path,
                                     integrity_path:Path,
                                     output_dir:Path)->dict:
    foundation,integrity=map(load_json,(foundation_path,integrity_path))
    errors=[]
    if foundation.get("stage")!="V78.91" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if integrity.get("stage")!="V78.92" or integrity.get("status")!="PASS":
        errors.append("integrity_input")

    required_summaries=[
        "release/v78_65/output/fill_portfolio_bridge_pipeline_summary_v78_61_to_v78_65.json",
        "release/v78_70/output/audit_reconciliation_pipeline_summary_v78_66_to_v78_70.json",
        "release/v78_75/output/performance_accounting_pipeline_summary_v78_71_to_v78_75.json",
        "release/v78_80/output/reporting_pipeline_summary_v78_76_to_v78_80.json",
        "release/v78_85/output/deployment_pipeline_summary_v78_81_to_v78_85.json",
        "release/v78_90/output/operation_runtime_pipeline_summary_v78_86_to_v78_90.json",
    ]
    replay_records=[]
    missing=[]
    for idx,rel in enumerate(required_summaries,1):
        p=repository_root/rel
        if not p.is_file():
            missing.append(rel)
            continue
        doc=load_json(p)
        expected=digest_json({k:v for k,v in doc.items() if k!="pipeline_sha256"})
        replay_records.append({
            "sequence":idx,
            "summary_path":rel,
            "status":doc.get("status"),
            "pipeline_sha256":doc.get("pipeline_sha256"),
            "recomputed_pipeline_sha256":expected,
            "verified":doc.get("pipeline_sha256")==expected and doc.get("status")=="PASS",
            "actual_orders_submitted":doc.get("actual_orders_submitted"),
            "network_allowed":doc.get("network_allowed"),
            "broker_connected":doc.get("broker_connected"),
        })
    checks={
        "all_required_summaries_present":not missing,
        "all_replay_records_verified":all(x["verified"] for x in replay_records),
        "summary_count_matches":len(replay_records)==len(required_summaries),
        "all_actual_orders_zero":all(x["actual_orders_submitted"]==0 for x in replay_records),
        "all_network_disabled":all(x["network_allowed"] is False for x in replay_records),
        "all_brokers_disconnected":all(x["broker_connected"] is False for x in replay_records),
        "champion_candidate_consistent":foundation.get("champion_candidate",{}).get("candidate_id")=="802493bbc77a",
        "release_runtime_present":bool(foundation.get("release_id")) and bool(foundation.get("runtime_id")),
    }
    failed=[k for k,v in checks.items() if not v]
    if missing: errors.append("missing_replay_summaries")
    if failed: errors.append("end_to_end_replay_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.93.end_to_end_replay_validation.1",
        "stage":"V78.93","status":status,
        "replay_records":replay_records,
        "missing_summaries":missing,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_94_FINAL_SYSTEM_SAFETY_GATE",
    }
    doc["replay_validation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="replay_validation_sha256"})
    write_json(output_dir/"end_to_end_replay_validation_v78_93.json",doc)
    ver={"stage":"V78.93","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "replay_validation_sha256":doc["replay_validation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"end_to_end_replay_validation_verification_v78_93.json",ver)
    return doc

def run_final_system_safety_gate(foundation_path:Path,
                                 integrity_path:Path,
                                 replay_path:Path,
                                 output_dir:Path)->dict:
    foundation,integrity,replay=map(load_json,(foundation_path,integrity_path,replay_path))
    errors=[]
    for expected,doc in (("V78.91",foundation),("V78.92",integrity),("V78.93",replay)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks={
        "offline_final_scope":foundation.get("scope")=="OFFLINE_FINAL_SYSTEM_CERTIFICATION_ONLY",
        "integrity_checks_passed":integrity.get("failed_checks")==[],
        "replay_checks_passed":replay.get("failed_checks")==[],
        "module_chain_head_present":bool(integrity.get("module_chain_head")),
        "live_activation_disabled":foundation.get("final_system_certification",{}).get("allow_live_activation") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,integrity,replay)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,integrity,replay)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,integrity,replay)),
        "live_trading_not_authorized":all(x.get("live_trading_authorized") is False for x in (foundation,integrity,replay)),
        "live_deployment_not_approved":all(x.get("live_deployment_approved") is False for x in (foundation,integrity,replay)),
        "real_credentials_disabled":all(x.get("real_credentials_allowed") is False for x in (foundation,integrity,replay)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("final_system_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.94.final_system_safety_gate.1",
        "stage":"V78.94","status":status,
        "gate_scope":"OFFLINE_V78_FINAL_CERTIFICATION_ONLY",
        "decision":"ALLOW_OFFLINE_V78_FINAL_CERTIFICATE" if not errors else "BLOCK_V78_FINAL_CERTIFICATE",
        "live_activation_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_95_FINAL_SYSTEM_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"final_system_safety_gate_v78_94.json",doc)
    ver={"stage":"V78.94","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"final_system_safety_gate_verification_v78_94.json",ver)
    return doc

def issue_final_system_certificate(v91:Path,v92:Path,v93:Path,v94:Path,
                                   foundation_path:Path,
                                   integrity_path:Path,
                                   output_dir:Path)->dict:
    docs=list(map(load_json,(v91,v92,v93,v94)))
    foundation=load_json(foundation_path)
    integrity=load_json(integrity_path)
    expected=["V78.91","V78.92","V78.93","V78.94"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.95.final_system_certificate.1",
        "stage":"V78.95",
        "certificate_id":"AI-STOCK-BOT-V78-FINAL-OFFLINE-CERTIFICATE",
        "status":status,
        "decision":"v78_offline_system_certified" if not errors else "v78_final_certification_rejected",
        "certification_scope":"COMPLETE_OFFLINE_PAPER_TRADING_SYSTEM_ONLY",
        "system_id":foundation.get("final_system_certification",{}).get("system_id"),
        "system_version":foundation.get("final_system_certification",{}).get("system_version"),
        "release_id":foundation.get("release_id"),
        "runtime_id":foundation.get("runtime_id"),
        "module_chain_head":integrity.get("module_chain_head"),
        "champion_candidate":foundation.get("champion_candidate"),
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "live_deployment_approved":False,
        "live_activation_approved":False,
        "certified_stages":expected,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_96_RELEASE_ACCEPTANCE_FOUNDATION" if not errors else "REPAIR_V78_95",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"final_system_certificate_v78_95.json",cert)
    ver={"stage":"V78.95","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "system_id":cert["system_id"],
         "system_version":cert["system_version"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"final_system_certificate_verification_v78_95.json",ver)
    return cert
