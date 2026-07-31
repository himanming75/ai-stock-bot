from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json, zipfile

class RecoveryReleaseError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def safe_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()

@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    artifact_sha256: str
    verification_sha256: str
    next_phase: str
    output_files: tuple[str, ...]
    def as_dict(self) -> dict:
        return {
            "stage":self.stage,"status":self.status,
            "artifact_sha256":self.artifact_sha256,
            "verification_sha256":self.verification_sha256,
            "next_phase":self.next_phase,
            "output_files":list(self.output_files),
        }

def build_manifest(repository_root: Path, certificate_path: Path, output_dir: Path, expected_certificate_sha256: str) -> StageResult:
    if not certificate_path.is_file():
        raise RecoveryReleaseError(f"missing V77.10 certificate: {certificate_path}")
    source_sha=sha256_file(certificate_path)
    if expected_certificate_sha256 and source_sha != expected_certificate_sha256:
        raise RecoveryReleaseError("V77.10 certificate file SHA256 mismatch")
    source=load_json(certificate_path)
    if source.get("certificate_id") != "RECOVERY-AUDIT-V77.10":
        raise RecoveryReleaseError("unexpected V77.10 certificate id")
    files=[]
    for p in sorted(repository_root.rglob("*")):
        if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts and "__pycache__" not in p.parts and "output" not in p.parts:
            files.append({"path":safe_rel(p,repository_root),"sha256":sha256_file(p),"size_bytes":p.stat().st_size})
    manifest={
        "schema_version":"v77.11.recovery_release_manifest.1",
        "stage":"V77.11","status":"PASS","source_certificate_file_sha256":source_sha,
        "source_certificate_sha256":source.get("certificate_sha256"),
        "file_count":len(files),"files":files,
        "safety":{"environment":"offline","network_allowed":False,"broker_connected":False,
                  "actual_orders_submitted":0,"live_trading_authorized":False},
        "next_phase":"V77_12_RECOVERY_BUNDLE_BUILDER",
    }
    manifest["manifest_sha256"]=digest_json({k:v for k,v in manifest.items() if k!="manifest_sha256"})
    verification={
        "schema_version":"v77.11.recovery_release_manifest_verification.1","stage":"V77.11",
        "status":"PASS","verified":True,"error_count":0,"errors":[],
        "source_certificate_file_sha256":source_sha,"manifest_sha256":manifest["manifest_sha256"],
        "file_count":len(files),"next_phase":manifest["next_phase"],
    }
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    mf=output_dir/"recovery_release_manifest_v77_11.json"
    vf=output_dir/"recovery_release_manifest_verification_v77_11.json"
    write_json(mf,manifest);write_json(vf,verification)
    return StageResult("V77.11","PASS",manifest["manifest_sha256"],verification["verification_sha256"],manifest["next_phase"],(str(mf),str(vf)))

def build_bundle(repository_root: Path, manifest_path: Path, output_dir: Path) -> StageResult:
    manifest=load_json(manifest_path)
    if manifest.get("status")!="PASS" or manifest.get("stage")!="V77.11":
        raise RecoveryReleaseError("invalid V77.11 manifest")
    output_dir.mkdir(parents=True,exist_ok=True)
    bundle=output_dir/"recovery_bundle_v77_12.zip"
    inventory=[]
    with zipfile.ZipFile(bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for item in manifest["files"]:
            p=repository_root/item["path"]
            if not p.is_file() or sha256_file(p)!=item["sha256"]:
                raise RecoveryReleaseError(f"manifest drift: {item['path']}")
            z.write(p,item["path"])
            inventory.append(item)
        z.writestr("META/recovery_release_manifest_v77_11.json",canonical(manifest)+"\n")
    bundle_sha=sha256_file(bundle)
    report={
        "schema_version":"v77.12.recovery_bundle_builder.1","stage":"V77.12","status":"PASS",
        "source_manifest_sha256":manifest["manifest_sha256"],"bundle_sha256":bundle_sha,
        "bundled_file_count":len(inventory),"bundle_filename":bundle.name,
        "safety":{"environment":"offline","network_allowed":False,"broker_connected":False,
                  "actual_orders_submitted":0,"live_trading_authorized":False},
        "next_phase":"V77_13_RECOVERY_BUNDLE_INTEGRITY_VERIFICATION",
    }
    report["report_sha256"]=digest_json({k:v for k,v in report.items() if k!="report_sha256"})
    verification={"schema_version":"v77.12.recovery_bundle_builder_verification.1","stage":"V77.12",
        "status":"PASS","verified":True,"error_count":0,"errors":[],"bundle_sha256":bundle_sha,
        "report_sha256":report["report_sha256"],"next_phase":report["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    rf=output_dir/"recovery_bundle_builder_v77_12.json";vf=output_dir/"recovery_bundle_builder_verification_v77_12.json"
    write_json(rf,report);write_json(vf,verification)
    return StageResult("V77.12","PASS",bundle_sha,verification["verification_sha256"],report["next_phase"],(str(bundle),str(rf),str(vf)))

def verify_bundle(bundle_path: Path, manifest_path: Path, output_dir: Path) -> StageResult:
    manifest=load_json(manifest_path)
    errors=[]
    with zipfile.ZipFile(bundle_path,"r") as z:
        names=set(z.namelist())
        for item in manifest["files"]:
            if item["path"] not in names:
                errors.append("missing:"+item["path"]);continue
            if hashlib.sha256(z.read(item["path"])).hexdigest()!=item["sha256"]:
                errors.append("hash:"+item["path"])
        if "META/recovery_release_manifest_v77_11.json" not in names:
            errors.append("missing:embedded_manifest")
    status="PASS" if not errors else "FAIL"
    result={"schema_version":"v77.13.recovery_bundle_integrity_verification.1","stage":"V77.13",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "bundle_sha256":sha256_file(bundle_path),"source_manifest_sha256":manifest["manifest_sha256"],
        "verified_file_count":len(manifest["files"]) if not errors else len(manifest["files"])-len(errors),
        "safety":{"environment":"offline","network_allowed":False,"broker_connected":False,
                  "actual_orders_submitted":0,"live_trading_authorized":False},
        "next_phase":"V77_14_RECOVERY_INSTALLATION_VALIDATOR" if not errors else "REPAIR_V77_13"}
    result["verification_sha256"]=digest_json({k:v for k,v in result.items() if k!="verification_sha256"})
    vf=output_dir/"recovery_bundle_integrity_verification_v77_13.json";write_json(vf,result)
    return StageResult("V77.13",status,result["bundle_sha256"],result["verification_sha256"],result["next_phase"],(str(vf),))

def validate_installation(bundle_path: Path, manifest_path: Path, output_dir: Path) -> StageResult:
    manifest=load_json(manifest_path)
    staging=output_dir/"staging"
    if staging.exists():
        import shutil;shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(bundle_path,"r") as z:z.extractall(staging)
    errors=[]
    for item in manifest["files"]:
        p=staging/item["path"]
        if not p.is_file():errors.append("missing:"+item["path"])
        elif sha256_file(p)!=item["sha256"]:errors.append("hash:"+item["path"])
    critical=["broker/recovery_release_pipeline_v77_11_15.py",
              "tools/recovery_release_manifest_v77_11.py",
              "tools/recovery_bundle_builder_v77_12.py",
              "tools/recovery_bundle_integrity_v77_13.py",
              "tools/recovery_installation_validator_v77_14.py"]
    for rel in critical:
        if not (staging/rel).is_file():errors.append("critical:"+rel)
    status="PASS" if not errors else "FAIL"
    attestation={"schema_version":"v77.14.recovery_installation_validator.1","stage":"V77.14",
        "status":status,"installation_valid":not errors,"error_count":len(errors),"errors":errors,
        "bundle_sha256":sha256_file(bundle_path),"installed_file_count":len(manifest["files"])-len(errors),
        "critical_file_count":len(critical),"execution_mode":"staged_offline_validation",
        "safety":{"environment":"offline","network_allowed":False,"broker_connected":False,
                  "actual_orders_submitted":0,"live_trading_authorized":False},
        "next_phase":"V77_15_RECOVERY_RELEASE_CERTIFICATE" if not errors else "REPAIR_V77_14"}
    attestation["attestation_sha256"]=digest_json({k:v for k,v in attestation.items() if k!="attestation_sha256"})
    verification={"schema_version":"v77.14.recovery_installation_validator_verification.1","stage":"V77.14",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "attestation_sha256":attestation["attestation_sha256"],"bundle_sha256":attestation["bundle_sha256"],
        "next_phase":attestation["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    af=output_dir/"recovery_installation_attestation_v77_14.json"
    vf=output_dir/"recovery_installation_validator_verification_v77_14.json"
    write_json(af,attestation);write_json(vf,verification)
    return StageResult("V77.14",status,attestation["attestation_sha256"],verification["verification_sha256"],attestation["next_phase"],(str(af),str(vf)))

def issue_release_certificate(v11: Path, v12: Path, v13: Path, v14: Path, output_dir: Path) -> StageResult:
    docs=[load_json(p) for p in (v11,v12,v13,v14)]
    errors=[]
    expected=["V77.11","V77.12","V77.13","V77.14"]
    for e,d in zip(expected,docs):
        if d.get("stage")!=e or d.get("status")!="PASS":errors.append(e)
    status="PASS" if not errors else "FAIL"
    anchors={
        "v77_11_verification_sha256":docs[0].get("verification_sha256"),
        "v77_12_verification_sha256":docs[1].get("verification_sha256"),
        "v77_13_verification_sha256":docs[2].get("verification_sha256"),
        "v77_14_verification_sha256":docs[3].get("verification_sha256"),
    }
    cert={"schema_version":"v77.15.recovery_release_certificate.1","stage":"V77.15",
        "certificate_id":"RECOVERY-RELEASE-V77.15","status":status,
        "decision":"recovery_release_certified" if not errors else "recovery_release_rejected",
        "certified_stages":expected,"stage_count":4,"anchors":anchors,
        "safety":{"environment":"offline","network_allowed":False,"broker_connected":False,
                  "actual_orders_submitted":0,"live_trading_authorized":False},
        "error_count":len(errors),"errors":errors,
        "next_phase":"V77_16_PAPER_RUNTIME_SESSION_ORCHESTRATOR" if not errors else "REPAIR_V77_15"}
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    verification={"schema_version":"v77.15.recovery_release_certificate_verification.1","stage":"V77.15",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],"stage_count":4,"next_phase":cert["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    cf=output_dir/"recovery_release_certificate_v77_15.json"
    vf=output_dir/"recovery_release_certificate_verification_v77_15.json"
    write_json(cf,cert);write_json(vf,verification)
    return StageResult("V77.15",status,cert["certificate_sha256"],verification["verification_sha256"],cert["next_phase"],(str(cf),str(vf)))
