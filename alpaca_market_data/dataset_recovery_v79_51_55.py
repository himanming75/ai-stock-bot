from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def canonical_json(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha256_json(v:Any)->str:return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def sha256_bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def write_json(p:Path,v:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
def atomic_write(p:Path,data:bytes)->None:
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(mode="wb",delete=False,dir=p.parent,prefix=p.name,suffix=".tmp") as h:h.write(data);t=Path(h.name)
 os.replace(t,p)

@dataclass(frozen=True)
class RecoveryConfig:
 stage:str="V79.51";dataset_name:str="alpaca_historical_bars";prefer_active_version:bool=True;require_verified_retention_certificate:bool=True;preserve_source_version:bool=True;overwrite_existing_recovery:bool=False;allow_network:bool=False;allow_credentials:bool=False;allow_trading_client:bool=False;allow_order_submission:bool=False;actual_orders_submitted:int=0
 def validate(self)->None:
  if not self.dataset_name:raise ValueError("dataset_name is required")
  if not self.prefer_active_version or not self.require_verified_retention_certificate or not self.preserve_source_version:raise ValueError("strict recovery gates required")
  if self.overwrite_existing_recovery:raise ValueError("recovery overwrite prohibited")
  if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:raise ValueError("offline safety violation")
@dataclass(frozen=True)
class RecoveryPoint:
 stage:str;version_id:str;source_kind:str;dataset_sha256:str;metadata_sha256:str;row_count:int;byte_size:int;is_active:bool
 def to_dict(self):return asdict(self)

def validate_retention_certificate(path:Path)->dict:
 if not path.is_file():raise FileNotFoundError(path)
 c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
 if e!=sha256_json(u) or c.get("stage")!="V79.50" or c.get("status")!="PASS":raise ValueError("invalid V79.50 certificate")
 s=c.get("retention_summary",{})
 if s.get("deleted_version_count")!=0 or s.get("source_versions_preserved") is not True:raise ValueError("unsafe retention state")
 return c

def load_registry(path:Path)->dict:
 if not path.is_file():raise FileNotFoundError(path)
 r=json.loads(path.read_text(encoding="utf-8"));u=dict(r);e=u.pop("registry_sha256",None)
 if e!=sha256_json(u):raise ValueError("registry hash mismatch")
 v=r.get("versions")
 if not isinstance(v,list) or not v or r.get("version_count")!=len(v):raise ValueError("invalid registry")
 if r.get("active_version_id") not in {x.get("version_id") for x in v}:raise ValueError("active version missing")
 return r

def discover_recovery_points(registry:dict,versions_dir:Path,archive_dir:Path|None,config:RecoveryConfig)->list[RecoveryPoint]:
 config.validate();points=[];active=registry["active_version_id"]
 for item in registry["versions"]:
  vid=item["version_id"];choices=[("PRIMARY",versions_dir/vid)]
  if archive_dir is not None:choices.append(("ARCHIVE",archive_dir/vid))
  chosen=None
  for kind,d in choices:
   dp=d/f"{config.dataset_name}.jsonl";mp=d/"version_metadata.json"
   if dp.is_file() and mp.is_file():chosen=(kind,dp,mp);break
  if chosen is None:continue
  kind,dp,mp=chosen;db=dp.read_bytes();m=json.loads(mp.read_text(encoding="utf-8"));u=dict(m);mh=u.pop("metadata_sha256",None)
  if sha256_bytes(db)!=item["dataset_sha256"] or mh!=sha256_json(u) or m.get("version_id")!=vid:raise ValueError("invalid recovery point")
  points.append(RecoveryPoint("V79.51",vid,kind,item["dataset_sha256"],mh,item["row_count"],len(db),vid==active))
 if not points:raise ValueError("no recovery points")
 return sorted(points,key=lambda p:(not p.is_active,p.version_id))

def select_recovery_point(points:list[RecoveryPoint],config:RecoveryConfig)->RecoveryPoint:
 config.validate()
 for p in points:
  if p.is_active:return p
 raise ValueError("active recovery point unavailable")

def validate_recovery_source(point:RecoveryPoint,versions_dir:Path,archive_dir:Path|None,config:RecoveryConfig)->dict:
 base=versions_dir if point.source_kind=="PRIMARY" else archive_dir
 if base is None:raise ValueError("source unavailable")
 d=base/point.version_id;dp=d/f"{config.dataset_name}.jsonl";mp=d/"version_metadata.json";db=dp.read_bytes();m=json.loads(mp.read_text(encoding="utf-8"));u=dict(m);mh=u.pop("metadata_sha256",None)
 if sha256_bytes(db)!=point.dataset_sha256 or mh!=sha256_json(u) or mh!=point.metadata_sha256:raise ValueError("source changed")
 lines=[x for x in db.splitlines() if x.strip()]
 if len(lines)!=point.row_count:raise ValueError("row count mismatch")
 for x in lines:json.loads(x)
 return {"stage":"V79.52","status":"PASS","version_id":point.version_id,"source_kind":point.source_kind,"dataset_sha256":point.dataset_sha256,"metadata_sha256":point.metadata_sha256,"row_count":len(lines),"byte_size":len(db),"dataset_path":dp,"metadata_path":mp}

def execute_recovery(v:dict,recovery_dir:Path,config:RecoveryConfig)->dict:
 config.validate();td=recovery_dir/v["version_id"];dt=td/f"{config.dataset_name}.recovered.jsonl";mt=td/"recovered_version_metadata.json";db=Path(v["dataset_path"]).read_bytes();mb=Path(v["metadata_path"]).read_bytes()
 if td.exists():
  if not dt.is_file() or not mt.is_file() or dt.read_bytes()!=db or mt.read_bytes()!=mb:raise ValueError("recovery conflict")
  created=False;reused=True
 else:
  td.mkdir(parents=True);atomic_write(dt,db);atomic_write(mt,mb);created=True;reused=False
 if sha256_bytes(dt.read_bytes())!=v["dataset_sha256"]:raise ValueError("recovered hash mismatch")
 return {"stage":"V79.53","status":"PASS","version_id":v["version_id"],"created":created,"reused_existing_recovery":reused,"source_preserved":Path(v["dataset_path"]).is_file(),"recovered_dataset_relative_path":str(dt.relative_to(recovery_dir)).replace("\\","/"),"recovered_metadata_relative_path":str(mt.relative_to(recovery_dir)).replace("\\","/"),"dataset_sha256":v["dataset_sha256"],"metadata_sha256":v["metadata_sha256"],"row_count":v["row_count"],"byte_size":v["byte_size"]}

def write_recovery_outputs(out:Path,points:list[RecoveryPoint],selected:RecoveryPoint,validation:dict,execution:dict)->dict:
 out.mkdir(parents=True,exist_ok=True);pp=out/"dataset_recovery_points.json";lp=out/"dataset_recovery_execution_ledger.json"
 pd={"schema_version":"v79.51.recovery_points.1","stage":"V79.51","recovery_point_count":len(points),"selected_version_id":selected.version_id,"points":[p.to_dict() for p in points]}
 vd={k:v for k,v in validation.items() if k not in {"dataset_path","metadata_path"}}
 ledger={"schema_version":"v79.54.recovery_execution_ledger.1","stage":"V79.54","status":"PASS","selected_recovery_point":selected.to_dict(),"source_validation":vd,"execution":execution,"source_versions_preserved":execution["source_preserved"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0};ledger["ledger_sha256"]=sha256_json(ledger)
 write_json(pp,pd);write_json(lp,ledger)
 rd=out/"recovery"/execution["recovered_dataset_relative_path"];rm=out/"recovery"/execution["recovered_metadata_relative_path"]
 man={"schema_version":"v79.54.recovery_manifest.1","stage":"V79.54","version_id":selected.version_id,"recovery_point_count":len(points),"row_count":execution["row_count"],"source_versions_preserved":execution["source_preserved"],"files":{},"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
 for n,p in (("recovery_points",pp),("execution_ledger",lp),("recovered_dataset",rd),("recovered_metadata",rm)):
  b=p.read_bytes();man["files"][n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":sha256_bytes(b),"byte_size":len(b)}
 man["manifest_sha256"]=sha256_json(man);write_json(out/"dataset_recovery_manifest_v79_54.json",man);return man

def verify_recovery_manifest(out:Path,man:dict)->bool:
 u=dict(man);e=u.pop("manifest_sha256",None)
 if e!=sha256_json(u):raise ValueError("manifest hash mismatch")
 for i in man["files"].values():
  p=out/i["relative_path"];b=p.read_bytes()
  if sha256_bytes(b)!=i["sha256"] or len(b)!=i["byte_size"]:raise ValueError("manifest file mismatch")
 return True

def run_dataset_recovery(registry_path:Path,versions_dir:Path,archive_dir:Path|None,retention_certificate_path:Path,config:RecoveryConfig,output_dir:Path)->dict:
 config.validate();validate_retention_certificate(retention_certificate_path);r=load_registry(registry_path);points=discover_recovery_points(r,versions_dir,archive_dir,config);s=select_recovery_point(points,config);v=validate_recovery_source(s,versions_dir,archive_dir,config);x=execute_recovery(v,output_dir/"recovery",config);m=write_recovery_outputs(output_dir,points,s,v,x);verify_recovery_manifest(output_dir,m)
 return {"stage":"V79.54","status":"PASS","recovery_points":[p.to_dict() for p in points],"selected":s.to_dict(),"validation":{k:z for k,z in v.items() if k not in {"dataset_path","metadata_path"}},"execution":x,"manifest":m,"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_recovery_certificate(root:Path,out:Path,config:RecoveryConfig,result:dict)->dict:
 checks={"v79_50_certificate_present":(root/"release/v79_50/output/historical_dataset_retention_certificate_v79_50.json").is_file(),"recovery_status_pass":result["status"]=="PASS","active_version_selected":result["selected"]["is_active"] is True,"source_validation_pass":result["validation"]["status"]=="PASS","recovered_hash_matches":result["execution"]["dataset_sha256"]==result["selected"]["dataset_sha256"],"row_count_matches":result["execution"]["row_count"]==result["selected"]["row_count"],"source_preserved":result["execution"]["source_preserved"] is True,"manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,"network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,"trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
 failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
 cert={"schema_version":"v79.55.recovery_certificate.1","stage":"V79.55","status":status,"scope":"OFFLINE_HISTORICAL_DATASET_RECOVERY","stages_completed":["V79.51","V79.52","V79.53","V79.54","V79.55"],"passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),"config":asdict(config),"recovery_summary":{"recovery_point_count":len(result["recovery_points"]),"selected_version_id":result["selected"]["version_id"],"source_kind":result["selected"]["source_kind"],"row_count":result["execution"]["row_count"],"byte_size":result["execution"]["byte_size"],"created":result["execution"]["created"],"reused_existing_recovery":result["execution"]["reused_existing_recovery"],"source_preserved":result["execution"]["source_preserved"]},"recovery_manifest":result["manifest"],"checks":checks,"failed_checks":failed,"network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,"actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_56_HISTORICAL_DATASET_BACKUP_RESTORE"};cert["certificate_sha256"]=sha256_json(cert)
 cp=out/"historical_dataset_recovery_certificate_v79_55.json";write_json(cp,cert);write_json(out/"historical_dataset_recovery_verify_v79_55.json",{"stage":"V79.55","status":status,"verified":not failed,"certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(root)).replace("\\","/"),"failed_checks":failed});return cert
sha256_recovery_json=sha256_json
load_recovery_registry=load_registry
validate_recovery_retention_certificate=validate_retention_certificate
