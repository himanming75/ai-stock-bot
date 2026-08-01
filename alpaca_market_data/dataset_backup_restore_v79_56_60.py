from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import hashlib, json, os, tempfile, zipfile


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")

def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=path.parent, prefix=path.name, suffix=".tmp") as h:
        h.write(data); tmp=Path(h.name)
    os.replace(tmp,path)

@dataclass(frozen=True)
class BackupRestoreConfig:
    stage: str="V79.56"
    dataset_name: str="alpaca_historical_bars"
    backup_kind: str="FULL"
    compression: str="DEFLATED"
    require_recovery_certificate: bool=True
    preserve_source: bool=True
    overwrite_existing_backup: bool=False
    overwrite_existing_restore: bool=False
    allow_network: bool=False
    allow_credentials: bool=False
    allow_trading_client: bool=False
    allow_order_submission: bool=False
    actual_orders_submitted: int=0
    def validate(self)->None:
        if self.backup_kind!="FULL" or self.compression!="DEFLATED": raise ValueError("only FULL/DEFLATED supported")
        if not self.require_recovery_certificate or not self.preserve_source: raise ValueError("certificate and source preservation required")
        if self.overwrite_existing_backup or self.overwrite_existing_restore: raise ValueError("overwrite prohibited")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission: raise ValueError("offline backup only")
        if self.actual_orders_submitted!=0: raise ValueError("actual orders must remain zero")

@dataclass(frozen=True)
class BackupPlan:
    stage:str; version_id:str; backup_id:str; dataset_sha256:str; metadata_sha256:str; row_count:int; byte_size:int
    def to_dict(self): return asdict(self)

def validate_recovery_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(f"recovery certificate missing: {path}")
    cert=json.loads(path.read_text(encoding="utf-8")); unsigned=dict(cert); expected=unsigned.pop("certificate_sha256",None)
    if expected!=sha256_json(unsigned): raise ValueError("recovery certificate hash mismatch")
    if cert.get("stage")!="V79.55" or cert.get("status")!="PASS": raise ValueError("V79.55 recovery certificate is not PASS")
    if cert.get("recovery_summary",{}).get("source_preserved") is not True: raise ValueError("recovery source not preserved")
    return cert

def build_backup_plan(recovery_output:Path, cert:dict[str,Any], config:BackupRestoreConfig)->BackupPlan:
    config.validate(); summary=cert["recovery_summary"]; version_id=summary["selected_version_id"]
    base=recovery_output/"recovery"/version_id
    dataset=base/f"{config.dataset_name}.recovered.jsonl"; metadata=base/"recovered_version_metadata.json"
    if not dataset.is_file() or not metadata.is_file(): raise FileNotFoundError("recovery payload missing")
    db=dataset.read_bytes(); mb=metadata.read_bytes(); lines=[x for x in db.splitlines() if x.strip()]
    for i,line in enumerate(lines,1):
        try: json.loads(line)
        except Exception as e: raise ValueError(f"invalid recovered JSONL line {i}") from e
    dsha=sha256_bytes(db); msha=sha256_bytes(mb); backup_id=f"backup-{version_id}-{dsha[:12]}"
    return BackupPlan("V79.56",version_id,backup_id,dsha,msha,len(lines),len(db))

def create_backup_archive(recovery_output:Path, plan:BackupPlan, config:BackupRestoreConfig, backup_dir:Path)->dict[str,Any]:
    config.validate(); source=recovery_output/"recovery"/plan.version_id
    dataset=source/f"{config.dataset_name}.recovered.jsonl"; metadata=source/"recovered_version_metadata.json"
    archive=backup_dir/f"{plan.backup_id}.zip"; catalog=backup_dir/f"{plan.backup_id}.catalog.json"
    catalog_doc={"schema_version":"v79.57.backup_catalog.1","stage":"V79.57",**plan.to_dict(),"members":[
        {"path":f"payload/{config.dataset_name}.jsonl","sha256":plan.dataset_sha256,"byte_size":dataset.stat().st_size},
        {"path":"payload/version_metadata.json","sha256":plan.metadata_sha256,"byte_size":metadata.stat().st_size}],"source_preserved":True}
    catalog_doc["catalog_sha256"]=sha256_json(catalog_doc); catalog_bytes=(json.dumps(catalog_doc,indent=2,sort_keys=True)+"\n").encode()
    if archive.exists() or catalog.exists():
        if not archive.is_file() or not catalog.is_file(): raise ValueError("existing backup incomplete")
        if json.loads(catalog.read_text())!=catalog_doc: raise ValueError("backup catalog conflict")
        created=False; reused=True
    else:
        backup_dir.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"payload/{config.dataset_name}.jsonl",dataset.read_bytes())
            z.writestr("payload/version_metadata.json",metadata.read_bytes())
            z.writestr("backup_catalog.json",catalog_bytes)
        _atomic_write(catalog,catalog_bytes); created=True; reused=False
    return {"stage":"V79.57","status":"PASS","backup_id":plan.backup_id,"archive_path":archive,"catalog_path":catalog,"archive_sha256":sha256_bytes(archive.read_bytes()),"archive_byte_size":archive.stat().st_size,"created":created,"reused_existing_backup":reused,"source_preserved":dataset.is_file()}

def restore_backup(backup:dict[str,Any], plan:BackupPlan, config:BackupRestoreConfig, restore_dir:Path)->dict[str,Any]:
    config.validate(); archive=Path(backup["archive_path"]); target=restore_dir/plan.backup_id
    dataset_target=target/f"{config.dataset_name}.restored.jsonl"; metadata_target=target/"restored_version_metadata.json"
    with zipfile.ZipFile(archive,"r") as z:
        names=z.namelist();
        for name in names:
            p=PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts: raise ValueError("unsafe archive member")
        required={f"payload/{config.dataset_name}.jsonl","payload/version_metadata.json","backup_catalog.json"}
        if not required.issubset(names): raise ValueError("backup archive members missing")
        db=z.read(f"payload/{config.dataset_name}.jsonl"); mb=z.read("payload/version_metadata.json"); cat=json.loads(z.read("backup_catalog.json"))
    unsigned=dict(cat); expected=unsigned.pop("catalog_sha256",None)
    if expected!=sha256_json(unsigned): raise ValueError("embedded catalog hash mismatch")
    if sha256_bytes(db)!=plan.dataset_sha256 or sha256_bytes(mb)!=plan.metadata_sha256: raise ValueError("backup payload hash mismatch")
    if target.exists():
        if not dataset_target.is_file() or not metadata_target.is_file(): raise ValueError("existing restore incomplete")
        if dataset_target.read_bytes()!=db or metadata_target.read_bytes()!=mb: raise ValueError("existing restore conflict")
        created=False; reused=True
    else:
        target.mkdir(parents=True,exist_ok=False); _atomic_write(dataset_target,db); _atomic_write(metadata_target,mb); created=True; reused=False
    rows=len([x for x in db.splitlines() if x.strip()])
    if rows!=plan.row_count: raise ValueError("restored row count mismatch")
    return {"stage":"V79.58","status":"PASS","backup_id":plan.backup_id,"version_id":plan.version_id,"created":created,"reused_existing_restore":reused,"row_count":rows,"dataset_sha256":sha256_bytes(dataset_target.read_bytes()),"metadata_sha256":sha256_bytes(metadata_target.read_bytes()),"source_backup_preserved":archive.is_file(),"restored_dataset_relative_path":str(dataset_target.relative_to(restore_dir)).replace("\\","/"),"restored_metadata_relative_path":str(metadata_target.relative_to(restore_dir)).replace("\\","/")}

def write_backup_restore_outputs(output_dir:Path, plan:BackupPlan, backup:dict[str,Any], restore:dict[str,Any])->dict[str,Any]:
    plan_path=output_dir/"dataset_backup_plan.json"; ledger_path=output_dir/"dataset_backup_restore_ledger.json"
    plan_doc={"schema_version":"v79.56.backup_plan.1",**plan.to_dict()}
    ledger={"schema_version":"v79.59.backup_restore_ledger.1","stage":"V79.59","status":"PASS","plan":plan.to_dict(),"backup":{k:v for k,v in backup.items() if k not in {"archive_path","catalog_path"}},"restore":restore,"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=sha256_json(ledger); write_json(plan_path,plan_doc); write_json(ledger_path,ledger)
    archive=Path(backup["archive_path"]); catalog=Path(backup["catalog_path"]); restored_dataset=output_dir/"restore"/restore["restored_dataset_relative_path"]; restored_metadata=output_dir/"restore"/restore["restored_metadata_relative_path"]
    manifest={"schema_version":"v79.59.backup_restore_manifest.1","stage":"V79.59","backup_id":plan.backup_id,"version_id":plan.version_id,"row_count":plan.row_count,"files":{},"source_preserved":backup["source_preserved"],"backup_preserved":restore["source_backup_preserved"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    for name,path in (("plan",plan_path),("ledger",ledger_path),("archive",archive),("catalog",catalog),("restored_dataset",restored_dataset),("restored_metadata",restored_metadata)):
        data=path.read_bytes(); manifest["files"][name]={"relative_path":str(path.relative_to(output_dir)).replace("\\","/"),"sha256":sha256_bytes(data),"byte_size":len(data)}
    manifest["manifest_sha256"]=sha256_json(manifest); write_json(output_dir/"dataset_backup_restore_manifest_v79_59.json",manifest); return manifest

def verify_backup_restore_manifest(output_dir:Path, manifest:dict[str,Any])->bool:
    unsigned=dict(manifest); expected=unsigned.pop("manifest_sha256",None)
    if expected!=sha256_json(unsigned): raise ValueError("backup manifest self-hash mismatch")
    for info in manifest["files"].values():
        path=output_dir/info["relative_path"]
        if not path.is_file(): raise ValueError("backup output missing")
        data=path.read_bytes()
        if sha256_bytes(data)!=info["sha256"] or len(data)!=info["byte_size"]: raise ValueError("backup output integrity mismatch")
    return True

def run_backup_restore(recovery_output:Path,recovery_certificate:Path,config:BackupRestoreConfig,output_dir:Path)->dict[str,Any]:
    cert=validate_recovery_certificate(recovery_certificate); plan=build_backup_plan(recovery_output,cert,config); backup=create_backup_archive(recovery_output,plan,config,output_dir/"backups"); restore=restore_backup(backup,plan,config,output_dir/"restore"); manifest=write_backup_restore_outputs(output_dir,plan,backup,restore); verify_backup_restore_manifest(output_dir,manifest)
    return {"stage":"V79.59","status":"PASS","plan":plan.to_dict(),"backup":{k:v for k,v in backup.items() if k not in {"archive_path","catalog_path"}},"restore":restore,"manifest":manifest,"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_backup_restore_certificate(repository_root:Path,output_dir:Path,config:BackupRestoreConfig,result:dict[str,Any])->dict[str,Any]:
    checks={"v79_55_certificate_present":(repository_root/"release/v79_55/output/historical_dataset_recovery_certificate_v79_55.json").is_file(),"pipeline_status_pass":result["status"]=="PASS","backup_created_or_reused":result["backup"]["created"] or result["backup"]["reused_existing_backup"],"restore_created_or_reused":result["restore"]["created"] or result["restore"]["reused_existing_restore"],"restored_hash_matches":result["restore"]["dataset_sha256"]==result["plan"]["dataset_sha256"],"row_count_matches":result["restore"]["row_count"]==result["plan"]["row_count"],"source_preserved":result["backup"]["source_preserved"] is True,"backup_preserved":result["restore"]["source_backup_preserved"] is True,"manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,"network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,"trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"schema_version":"v79.60.backup_restore_certificate.1","stage":"V79.60","status":status,"scope":"OFFLINE_HISTORICAL_DATASET_BACKUP_RESTORE","stages_completed":["V79.56","V79.57","V79.58","V79.59","V79.60"],"passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),"config":asdict(config),"backup_restore_summary":{"backup_id":result["plan"]["backup_id"],"version_id":result["plan"]["version_id"],"row_count":result["plan"]["row_count"],"archive_byte_size":result["backup"]["archive_byte_size"],"backup_created":result["backup"]["created"],"backup_reused":result["backup"]["reused_existing_backup"],"restore_created":result["restore"]["created"],"restore_reused":result["restore"]["reused_existing_restore"],"source_preserved":result["backup"]["source_preserved"],"backup_preserved":result["restore"]["source_backup_preserved"]},"backup_restore_manifest":result["manifest"],"checks":checks,"failed_checks":failed,"network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,"actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_61_HISTORICAL_FEATURE_STORE"}
    cert["certificate_sha256"]=sha256_json(cert); cp=output_dir/"historical_dataset_backup_restore_certificate_v79_60.json"; write_json(cp,cert); write_json(output_dir/"historical_dataset_backup_restore_verify_v79_60.json",{"stage":"V79.60","status":status,"verified":not failed,"certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(repository_root)).replace("\\","/"),"failed_checks":failed}); return cert

sha256_backup_json=sha256_json

validate_backup_recovery_certificate=validate_recovery_certificate
