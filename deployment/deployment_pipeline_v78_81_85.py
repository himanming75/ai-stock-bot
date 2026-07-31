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
class DeploymentArtifact:
    artifact_id: str
    source_relative_path: str
    artifact_type: str
    sha256: str
    byte_size: int

def classify_artifact(path: str) -> str:
    suffix=Path(path).suffix.lower()
    if suffix==".json": return "json"
    if suffix==".csv": return "csv"
    if suffix==".md": return "markdown"
    if suffix==".txt": return "text"
    if suffix==".ps1": return "powershell"
    if suffix==".py": return "python"
    return "binary"

def inspect_artifact(repository_root:Path, relative_path:str)->DeploymentArtifact:
    p=(repository_root/relative_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(relative_path)
    data=p.read_bytes()
    sha=digest_bytes(data)
    return DeploymentArtifact(
        artifact_id=f"DA-{sha[:16]}",
        source_relative_path=relative_path.replace("\\","/"),
        artifact_type=classify_artifact(relative_path),
        sha256=sha,
        byte_size=len(data),
    )

def verify_artifact(repository_root:Path, artifact:dict)->bool:
    p=repository_root/artifact["source_relative_path"]
    if not p.is_file():
        return False
    data=p.read_bytes()
    return (
        digest_bytes(data)==artifact["sha256"]
        and len(data)==int(artifact["byte_size"])
        and classify_artifact(artifact["source_relative_path"])==artifact["artifact_type"]
    )

def build_deployment_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.80" or cert.get("status")!="PASS":
        errors.append("reporting_certificate")
    if cert.get("certification_scope")!="OFFLINE_DEPLOYMENT_PACKAGING_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    deployment=config.get("deployment",{})
    for key in ("release_id","release_version","required_artifacts","target_environment","allow_live_deployment"):
        if key not in deployment:
            errors.append(f"config_{key}")
    if deployment.get("target_environment")!="offline":
        errors.append("target_environment")
    if deployment.get("allow_live_deployment") is not False:
        errors.append("live_deployment_flag")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.81.deployment_foundation.1",
        "stage":"V78.81","status":status,
        "scope":"OFFLINE_DEPLOYMENT_PACKAGE_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "deployment":deployment,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_82_DEPLOYMENT_PACKAGE_BUILDER",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"deployment_foundation_v78_81.json",doc)
    ver={"stage":"V78.81","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deployment_foundation_verification_v78_81.json",ver)
    return doc

def run_deployment_package_builder(repository_root:Path,foundation_path:Path,output_dir:Path)->dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.81" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    artifacts=[]
    try:
        for rel in foundation.get("deployment",{}).get("required_artifacts",[]):
            artifacts.append(inspect_artifact(repository_root,str(rel)))
    except Exception as exc:
        errors.append(f"artifact_inspection_exception:{type(exc).__name__}")

    manifest={
        "schema_version":"v78.82.deployment_manifest.1",
        "release_id":foundation.get("deployment",{}).get("release_id"),
        "release_version":foundation.get("deployment",{}).get("release_version"),
        "target_environment":foundation.get("deployment",{}).get("target_environment"),
        "artifact_count":len(artifacts),
        "artifacts":[asdict(x) for x in artifacts],
        "source_certificate_stage":"V78.80",
        "offline_only":True,
    }
    manifest["manifest_sha256"]=digest_json({k:v for k,v in manifest.items() if k!="manifest_sha256"})
    write_json(output_dir/"deployment_manifest_v78_82.json",manifest)

    checks={
        "artifact_count_matches_required":len(artifacts)==len(
            foundation.get("deployment",{}).get("required_artifacts",[])
        ),
        "artifact_ids_unique":len({x.artifact_id for x in artifacts})==len(artifacts),
        "artifact_hashes_unique":len({x.sha256 for x in artifacts})==len(artifacts),
        "all_artifacts_nonempty":all(x.byte_size>0 for x in artifacts),
        "manifest_hash_valid":manifest["manifest_sha256"]==digest_json(
            {k:v for k,v in manifest.items() if k!="manifest_sha256"}
        ),
        "target_environment_offline":manifest["target_environment"]=="offline",
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("package_builder_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.82.deployment_package_builder.1",
        "stage":"V78.82","status":status,
        "manifest":manifest,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_83_DEPLOYMENT_VALIDATION",
    }
    doc["package_builder_sha256"]=digest_json({k:v for k,v in doc.items() if k!="package_builder_sha256"})
    write_json(output_dir/"deployment_package_builder_v78_82.json",doc)
    ver={"stage":"V78.82","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "package_builder_sha256":doc["package_builder_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deployment_package_builder_verification_v78_82.json",ver)
    return doc

def run_deployment_validation(repository_root:Path,foundation_path:Path,builder_path:Path,
                              output_dir:Path)->dict:
    foundation,builder=map(load_json,(foundation_path,builder_path))
    errors=[]
    if foundation.get("stage")!="V78.81" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if builder.get("stage")!="V78.82" or builder.get("status")!="PASS":
        errors.append("builder_input")
    manifest=builder.get("manifest",{})
    artifact_results=[]
    for artifact in manifest.get("artifacts",[]):
        artifact_results.append({
            "artifact_id":artifact["artifact_id"],
            "source_relative_path":artifact["source_relative_path"],
            "verified":verify_artifact(repository_root,artifact),
        })
    checks={
        "manifest_hash_valid":manifest.get("manifest_sha256")==digest_json(
            {k:v for k,v in manifest.items() if k!="manifest_sha256"}
        ),
        "all_artifacts_verified":all(x["verified"] for x in artifact_results),
        "artifact_count_consistent":len(artifact_results)==manifest.get("artifact_count"),
        "release_id_consistent":manifest.get("release_id")==foundation.get("deployment",{}).get("release_id"),
        "release_version_consistent":manifest.get("release_version")==foundation.get("deployment",{}).get("release_version"),
        "offline_only":manifest.get("offline_only") is True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("deployment_validation_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.83.deployment_validation.1",
        "stage":"V78.83","status":status,
        "artifact_validation":artifact_results,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_84_DEPLOYMENT_SAFETY_GATE",
    }
    doc["validation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="validation_sha256"})
    write_json(output_dir/"deployment_validation_v78_83.json",doc)
    ver={"stage":"V78.83","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "validation_sha256":doc["validation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deployment_validation_verification_v78_83.json",ver)
    return doc

def run_deployment_safety_gate(foundation_path:Path,builder_path:Path,
                               validation_path:Path,output_dir:Path)->dict:
    foundation,builder,validation=map(load_json,(foundation_path,builder_path,validation_path))
    errors=[]
    for expected,doc in (("V78.81",foundation),("V78.82",builder),("V78.83",validation)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks={
        "offline_deployment_scope":foundation.get("scope")=="OFFLINE_DEPLOYMENT_PACKAGE_ONLY",
        "builder_checks_passed":builder.get("failed_checks")==[],
        "validation_checks_passed":validation.get("failed_checks")==[],
        "target_environment_offline":foundation.get("deployment",{}).get("target_environment")=="offline",
        "live_deployment_disabled":foundation.get("deployment",{}).get("allow_live_deployment") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,builder,validation)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,builder,validation)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,builder,validation)),
        "live_trading_not_authorized":all(x.get("live_trading_authorized") is False for x in (foundation,builder,validation)),
        "real_credentials_disabled":all(x.get("real_credentials_allowed") is False for x in (foundation,builder,validation)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("deployment_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.84.deployment_safety_gate.1",
        "stage":"V78.84","status":status,
        "gate_scope":"OFFLINE_OPERATION_RUNTIME_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_OPERATION_RUNTIME" if not errors else "BLOCK_OPERATION_RUNTIME",
        "live_deployment_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_85_DEPLOYMENT_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"deployment_safety_gate_v78_84.json",doc)
    ver={"stage":"V78.84","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deployment_safety_gate_verification_v78_84.json",ver)
    return doc

def issue_deployment_certificate(v81:Path,v82:Path,v83:Path,v84:Path,
                                 foundation_path:Path,builder_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v81,v82,v83,v84)))
    foundation=load_json(foundation_path)
    builder=load_json(builder_path)
    expected=["V78.81","V78.82","V78.83","V78.84"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    manifest=builder.get("manifest",{})
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.85.deployment_certificate.1",
        "stage":"V78.85",
        "certificate_id":"DEPLOYMENT-V78.85",
        "status":status,
        "decision":"certified_for_offline_operation_runtime" if not errors else "deployment_rejected",
        "certification_scope":"OFFLINE_OPERATION_RUNTIME_DEVELOPMENT_ONLY",
        "release_id":manifest.get("release_id"),
        "release_version":manifest.get("release_version"),
        "manifest_sha256":manifest.get("manifest_sha256"),
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "live_deployment_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_86_OPERATION_RUNTIME_FOUNDATION" if not errors else "REPAIR_V78_85",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"deployment_certificate_v78_85.json",cert)
    ver={"stage":"V78.85","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "manifest_sha256":cert["manifest_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deployment_certificate_verification_v78_85.json",ver)
    return cert
