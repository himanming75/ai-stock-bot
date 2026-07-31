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
class AcceptanceArtifact:
    sequence: int
    relative_path: str
    artifact_type: str
    sha256: str
    byte_size: int
    previous_record_sha256: str
    record_sha256: str

def classify(path: str) -> str:
    suffix=Path(path).suffix.lower()
    return {
        ".json":"json",".csv":"csv",".md":"markdown",
        ".txt":"text",".ps1":"powershell",".py":"python"
    }.get(suffix,"binary")

def build_artifact_record(sequence:int, repository_root:Path, relative_path:str,
                          previous_record_sha256:str)->AcceptanceArtifact:
    p=repository_root/relative_path
    if not p.is_file():
        raise FileNotFoundError(relative_path)
    data=p.read_bytes()
    base={
        "sequence":sequence,
        "relative_path":relative_path.replace("\\","/"),
        "artifact_type":classify(relative_path),
        "sha256":digest_bytes(data),
        "byte_size":len(data),
        "previous_record_sha256":previous_record_sha256,
    }
    return AcceptanceArtifact(**base,record_sha256=digest_json(base))

def verify_artifact_chain(repository_root:Path, records:list[AcceptanceArtifact])->bool:
    previous=""
    for idx,record in enumerate(records,1):
        if record.sequence!=idx:
            raise ValueError("artifact sequence gap")
        if record.previous_record_sha256!=previous:
            raise ValueError("artifact chain mismatch")
        expected_record=digest_json({
            "sequence":record.sequence,
            "relative_path":record.relative_path,
            "artifact_type":record.artifact_type,
            "sha256":record.sha256,
            "byte_size":record.byte_size,
            "previous_record_sha256":record.previous_record_sha256,
        })
        if record.record_sha256!=expected_record:
            raise ValueError("artifact record hash mismatch")
        p=repository_root/record.relative_path
        if not p.is_file():
            raise ValueError("artifact missing")
        data=p.read_bytes()
        if digest_bytes(data)!=record.sha256 or len(data)!=record.byte_size:
            raise ValueError("artifact content mismatch")
        previous=record.record_sha256
    return True

def build_release_acceptance_foundation(final_certificate_path:Path,
                                        config_path:Path,
                                        output_dir:Path)->dict:
    cert,config=map(load_json,(final_certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.95" or cert.get("status")!="PASS":
        errors.append("final_system_certificate")
    if cert.get("certification_scope")!="COMPLETE_OFFLINE_PAPER_TRADING_SYSTEM_ONLY":
        errors.append("certificate_scope")
    acceptance=config.get("release_acceptance",{})
    for key in ("release_name","release_version","required_artifacts","acceptance_checks","allow_live_release"):
        if key not in acceptance:
            errors.append(f"config_{key}")
    if acceptance.get("allow_live_release") is not False:
        errors.append("live_release_flag")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.96.release_acceptance_foundation.1",
        "stage":"V78.96","status":status,
        "scope":"OFFLINE_FINAL_RELEASE_ACCEPTANCE_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "system_id":cert.get("system_id"),
        "system_version":cert.get("system_version"),
        "release_id":cert.get("release_id"),
        "runtime_id":cert.get("runtime_id"),
        "module_chain_head":cert.get("module_chain_head"),
        "release_acceptance":acceptance,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_97_RELEASE_ACCEPTANCE_CHECKLIST",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"release_acceptance_foundation_v78_96.json",doc)
    ver={"stage":"V78.96","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"release_acceptance_foundation_verification_v78_96.json",ver)
    return doc

def run_release_acceptance_checklist(repository_root:Path,
                                     foundation_path:Path,
                                     output_dir:Path)->dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.96" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("release_acceptance",{})
    required=cfg.get("required_artifacts",[])
    existence={rel:(repository_root/rel).is_file() for rel in required}
    checks={
        "all_required_artifacts_exist":all(existence.values()) if existence else False,
        "system_id_present":bool(foundation.get("system_id")),
        "release_id_present":bool(foundation.get("release_id")),
        "runtime_id_present":bool(foundation.get("runtime_id")),
        "module_chain_head_present":bool(foundation.get("module_chain_head")),
        "champion_candidate_present":bool(foundation.get("champion_candidate",{}).get("candidate_id")),
        "live_release_disabled":cfg.get("allow_live_release") is False,
        "acceptance_checklist_nonempty":len(cfg.get("acceptance_checks",[]))>0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("release_acceptance_checklist")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.97.release_acceptance_checklist.1",
        "stage":"V78.97","status":status,
        "artifact_existence":existence,
        "configured_acceptance_checks":cfg.get("acceptance_checks",[]),
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_98_RELEASE_ARTIFACT_VERIFICATION",
    }
    doc["checklist_sha256"]=digest_json({k:v for k,v in doc.items() if k!="checklist_sha256"})
    write_json(output_dir/"release_acceptance_checklist_v78_97.json",doc)
    ver={"stage":"V78.97","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "checklist_sha256":doc["checklist_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"release_acceptance_checklist_verification_v78_97.json",ver)
    return doc

def run_release_artifact_verification(repository_root:Path,
                                      foundation_path:Path,
                                      checklist_path:Path,
                                      output_dir:Path)->dict:
    foundation,checklist=map(load_json,(foundation_path,checklist_path))
    errors=[]
    if foundation.get("stage")!="V78.96" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if checklist.get("stage")!="V78.97" or checklist.get("status")!="PASS":
        errors.append("checklist_input")
    records=[]
    previous=""
    try:
        for idx,rel in enumerate(foundation.get("release_acceptance",{}).get("required_artifacts",[]),1):
            record=build_artifact_record(idx,repository_root,rel,previous)
            records.append(record)
            previous=record.record_sha256
        chain_verified=verify_artifact_chain(repository_root,records)
    except Exception as exc:
        chain_verified=False
        errors.append(f"artifact_verification_exception:{type(exc).__name__}")
    checks={
        "artifact_chain_verified":chain_verified,
        "artifact_count_matches":len(records)==len(
            foundation.get("release_acceptance",{}).get("required_artifacts",[])
        ),
        "record_hashes_unique":len({x.record_sha256 for x in records})==len(records),
        "artifact_hashes_unique":len({x.sha256 for x in records})==len(records),
        "all_artifacts_nonempty":all(x.byte_size>0 for x in records),
        "final_certificate_present":any("final_system_certificate_v78_95.json" in x.relative_path for x in records),
        "report_manifest_present":any("report_manifest_v78_78.json" in x.relative_path for x in records),
        "deployment_manifest_present":any("deployment_manifest_v78_82.json" in x.relative_path for x in records),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("release_artifact_checks")
    status="PASS" if not errors else "FAIL"
    manifest={
        "schema_version":"v78.98.final_release_manifest.1",
        "release_name":foundation.get("release_acceptance",{}).get("release_name"),
        "release_version":foundation.get("release_acceptance",{}).get("release_version"),
        "artifact_count":len(records),
        "artifact_chain_head":records[-1].record_sha256 if records else "",
        "artifacts":[asdict(x) for x in records],
    }
    manifest["manifest_sha256"]=digest_json({k:v for k,v in manifest.items() if k!="manifest_sha256"})
    write_json(output_dir/"final_release_manifest_v78_98.json",manifest)
    doc={
        "schema_version":"v78.98.release_artifact_verification.1",
        "stage":"V78.98","status":status,
        "final_release_manifest":manifest,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_99_RELEASE_ACCEPTANCE_SAFETY_GATE",
    }
    doc["artifact_verification_sha256"]=digest_json({k:v for k,v in doc.items() if k!="artifact_verification_sha256"})
    write_json(output_dir/"release_artifact_verification_v78_98.json",doc)
    ver={"stage":"V78.98","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "artifact_verification_sha256":doc["artifact_verification_sha256"],
         "manifest_sha256":manifest["manifest_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"release_artifact_verification_verification_v78_98.json",ver)
    return doc

def run_release_acceptance_safety_gate(foundation_path:Path,
                                       checklist_path:Path,
                                       artifact_path:Path,
                                       output_dir:Path)->dict:
    foundation,checklist,artifact=map(load_json,(foundation_path,checklist_path,artifact_path))
    errors=[]
    for expected,doc in (("V78.96",foundation),("V78.97",checklist),("V78.98",artifact)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks={
        "offline_release_scope":foundation.get("scope")=="OFFLINE_FINAL_RELEASE_ACCEPTANCE_ONLY",
        "checklist_passed":checklist.get("failed_checks")==[],
        "artifact_verification_passed":artifact.get("failed_checks")==[],
        "manifest_present":bool(artifact.get("final_release_manifest",{}).get("manifest_sha256")),
        "artifact_chain_head_present":bool(artifact.get("final_release_manifest",{}).get("artifact_chain_head")),
        "live_release_disabled":foundation.get("release_acceptance",{}).get("allow_live_release") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,checklist,artifact)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,checklist,artifact)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,checklist,artifact)),
        "live_trading_not_authorized":all(x.get("live_trading_authorized") is False for x in (foundation,checklist,artifact)),
        "live_deployment_not_approved":all(x.get("live_deployment_approved") is False for x in (foundation,checklist,artifact)),
        "real_credentials_disabled":all(x.get("real_credentials_allowed") is False for x in (foundation,checklist,artifact)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("release_acceptance_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.99.release_acceptance_safety_gate.1",
        "stage":"V78.99","status":status,
        "gate_scope":"OFFLINE_V78_FINAL_RELEASE_CERTIFICATE_ONLY",
        "decision":"ALLOW_OFFLINE_V78_FINAL_RELEASE_CERTIFICATE" if not errors else "BLOCK_V78_FINAL_RELEASE_CERTIFICATE",
        "release_ready":not errors,
        "live_release_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_100_FINAL_RELEASE_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"release_acceptance_safety_gate_v78_99.json",doc)
    ver={"stage":"V78.99","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "release_ready":doc["release_ready"],
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"release_acceptance_safety_gate_verification_v78_99.json",ver)
    return doc

def issue_final_release_certificate(v96:Path,v97:Path,v98:Path,v99:Path,
                                    foundation_path:Path,
                                    artifact_path:Path,
                                    output_dir:Path)->dict:
    docs=list(map(load_json,(v96,v97,v98,v99)))
    foundation=load_json(foundation_path)
    artifact=load_json(artifact_path)
    expected=["V78.96","V78.97","V78.98","V78.99"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    manifest=artifact.get("final_release_manifest",{})
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.100.final_release_certificate.1",
        "stage":"V78.100",
        "certificate_id":"AI-STOCK-BOT-V78.100-FINAL-RELEASE",
        "status":status,
        "decision":"v78_final_offline_release_accepted" if not errors else "v78_release_rejected",
        "certification_scope":"FINAL_OFFLINE_PAPER_TRADING_RELEASE_ONLY",
        "release_ready":not errors,
        "release_name":foundation.get("release_acceptance",{}).get("release_name"),
        "release_version":foundation.get("release_acceptance",{}).get("release_version"),
        "system_id":foundation.get("system_id"),
        "system_version":foundation.get("system_version"),
        "release_id":foundation.get("release_id"),
        "runtime_id":foundation.get("runtime_id"),
        "module_chain_head":foundation.get("module_chain_head"),
        "artifact_chain_head":manifest.get("artifact_chain_head"),
        "final_release_manifest_sha256":manifest.get("manifest_sha256"),
        "champion_candidate":foundation.get("champion_candidate"),
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "live_deployment_approved":False,
        "live_activation_approved":False,
        "live_release_approved":False,
        "certified_stages":expected,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V79_FOUNDATION" if not errors else "REPAIR_V78_100",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"final_release_certificate_v78_100.json",cert)
    ver={"stage":"V78.100","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "release_ready":cert["release_ready"],
         "certificate_sha256":cert["certificate_sha256"],
         "final_release_manifest_sha256":cert["final_release_manifest_sha256"],
         "release_name":cert["release_name"],
         "release_version":cert["release_version"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"final_release_certificate_verification_v78_100.json",ver)
    return cert
