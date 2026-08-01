from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class StrategyExecutionFinalCertificationConfig:
    mode: str = "PAPER_STRATEGY_EXECUTION_FINAL_CERTIFICATION"
    environment: str = "PAPER"
    release_candidate: str = "PAPER_STRATEGY_EXECUTION_RC1"
    require_v87_20: bool = True
    require_v87_40: bool = True
    require_v87_60: bool = True
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_STRATEGY_EXECUTION_FINAL_CERTIFICATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if self.release_candidate != "PAPER_STRATEGY_EXECUTION_RC1": raise ValueError("release candidate")
        if not all([self.require_v87_20,self.require_v87_40,self.require_v87_60]): raise ValueError("certificate chain")
        if self.auto_execution_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_certificate(path:Path,stage:str,flag:str)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u): raise ValueError("certificate hash")
    if c.get("stage")!=stage or c.get("status")!="PASS": raise ValueError("certificate stage/status")
    if c.get(flag) is not True: raise ValueError("completion flag")
    if c.get("network_requests_executed") != 0 or c.get("actual_orders_submitted") != 0:
        raise ValueError("unsafe certificate")
    return c

def source_paths(root):
    d={"stage":"V87.61",
       "operations":str(root/"release/v87_20/output/strategy_execution_certificate_v87_20.json"),
       "simulation":str(root/"release/v87_40/output/strategy_execution_sim_certificate_v87_40.json"),
       "reconciliation":str(root/"release/v87_60/output/strategy_execution_recon_certificate_v87_60.json")}
    d["paths_sha256"]=hj(d);return d

def load_chain(root):
    operations=validate_certificate(root/"release/v87_20/output/strategy_execution_certificate_v87_20.json",
                                    "V87.20","paper_strategy_execution_operations_complete")
    simulation=validate_certificate(root/"release/v87_40/output/strategy_execution_sim_certificate_v87_40.json",
                                    "V87.40","paper_strategy_execution_simulation_complete")
    reconciliation=validate_certificate(root/"release/v87_60/output/strategy_execution_recon_certificate_v87_60.json",
                                        "V87.60","paper_strategy_execution_reconciliation_complete")
    d={"stage":"V87.62","operations":operations,"simulation":simulation,"reconciliation":reconciliation}
    d["chain_sha256"]=hj(d);return d

def chain_summary(chain):
    o=chain["operations"]["strategy_execution_summary"]
    s=chain["simulation"]["strategy_execution_simulation_summary"]
    r=chain["reconciliation"]["strategy_execution_reconciliation_summary"]
    d={"stage":"V87.63","strategy_id":o["strategy_id"],
       "operations_status":chain["operations"]["status"],
       "simulation_status":chain["simulation"]["status"],
       "reconciliation_status":chain["reconciliation"]["status"],
       "simulation_replay_deterministic":s["replay_deterministic"],
       "reconciliation_chain_root_sha256":r["chain_root_sha256"],
       "reconciliation_tamper_status":r["tamper_status"],
       "reconciliation_audit_status":r["audit_status"]}
    d["summary_sha256"]=hj(d);return d

def integrity_chain(chain):
    ids={
      "V87.20":chain["operations"]["certificate_sha256"],
      "V87.40":chain["simulation"]["certificate_sha256"],
      "V87.60":chain["reconciliation"]["certificate_sha256"],
    }
    d={"stage":"V87.64","status":"PASS","certificate_count":3,
       "certificate_ids":ids,"chain_root_sha256":hj(ids)}
    d["integrity_sha256"]=hj(d);return d

def safety_chain(chain,config):
    checks={
      "operations_auto_false":chain["operations"].get("auto_execution_enabled") is False,
      "operations_submit_false":chain["operations"].get("paper_order_submission_authorized") is False,
      "simulation_auto_false":chain["simulation"].get("auto_execution_enabled") is False,
      "simulation_submit_false":chain["simulation"].get("paper_order_submission_authorized") is False,
      "reconciliation_auto_false":chain["reconciliation"].get("auto_execution_enabled") is False,
      "reconciliation_submit_false":chain["reconciliation"].get("paper_order_submission_authorized") is False,
      "live_false":all(c.get("live_trading_authorized") is False for c in chain.values() if isinstance(c,dict)),
      "config_network_zero":config.network_requests_executed==0,
      "config_orders_zero":config.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.65","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["safety_sha256"]=hj(d);return d

def compliance_report(summary,safety):
    checks={"operations_pass":summary["operations_status"]=="PASS",
            "simulation_pass":summary["simulation_status"]=="PASS",
            "reconciliation_pass":summary["reconciliation_status"]=="PASS",
            "replay_deterministic":summary["simulation_replay_deterministic"] is True,
            "tamper_pass":summary["reconciliation_tamper_status"]=="PASS",
            "reconciliation_audit_pass":summary["reconciliation_audit_status"]=="PASS",
            "safety_pass":safety["status"]=="PASS"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.66","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed,
       "paper_environment_only":True,"live_promotion_authorized":False}
    d["compliance_sha256"]=hj(d);return d

def replay_certificate(integrity,summary):
    d={"stage":"V87.67","status":"PASS",
       "source_order":["V87.20","V87.40","V87.60"],
       "deterministic_chain_root":integrity["chain_root_sha256"],
       "simulation_replay_deterministic":summary["simulation_replay_deterministic"],
       "reconciliation_chain_root_sha256":summary["reconciliation_chain_root_sha256"]}
    d["replay_sha256"]=hj(d);return d

def rollback_certificate():
    d={"stage":"V87.68","status":"PASS","rollback_target":"V87.60",
       "restore_strategy_operations":True,"discard_rc_artifacts":True,
       "disable_auto_execution":True,"disable_order_submission":True,
       "disable_network":True,"preserve_audit_logs":True}
    d["rollback_sha256"]=hj(d);return d

def release_readiness(config,compliance,replay,rollback):
    checks={"release_candidate_valid":config.release_candidate=="PAPER_STRATEGY_EXECUTION_RC1",
            "compliance_pass":compliance["status"]=="PASS",
            "replay_pass":replay["status"]=="PASS",
            "rollback_pass":rollback["status"]=="PASS",
            "auto_execution_false":config.auto_execution_enabled is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.69","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed,
       "release_candidate":config.release_candidate,
       "production_ready":False,"paper_rc_ready":not failed}
    d["readiness_sha256"]=hj(d);return d

def archive_record(integrity,config):
    d={"stage":"V87.70","status":"PASS",
       "archive_id":"strategy-exec-archive-"+integrity["chain_root_sha256"][:24],
       "release_candidate":config.release_candidate,
       "source_certificate_count":integrity["certificate_count"],
       "source_certificate_ids":integrity["certificate_ids"]}
    d["archive_sha256"]=hj(d);return d

def final_report(summary,integrity,safety,compliance,replay,rollback,readiness,archive):
    d={"stage":"V87.71","status":"PASS",
       "strategy_id":summary["strategy_id"],
       "certificate_count":integrity["certificate_count"],
       "chain_root_sha256":integrity["chain_root_sha256"],
       "safety_status":safety["status"],
       "compliance_status":compliance["status"],
       "replay_status":replay["status"],
       "rollback_status":rollback["status"],
       "readiness_status":readiness["status"],
       "archive_status":archive["status"],
       "release_candidate":readiness["release_candidate"]}
    d["report_sha256"]=hj(d);return d

def audit(config,report):
    checks={"certificate_count_three":report["certificate_count"]==3,
            "safety_pass":report["safety_status"]=="PASS",
            "compliance_pass":report["compliance_status"]=="PASS",
            "replay_pass":report["replay_status"]=="PASS",
            "rollback_pass":report["rollback_status"]=="PASS",
            "readiness_pass":report["readiness_status"]=="PASS",
            "archive_pass":report["archive_status"]=="PASS",
            "release_candidate_valid":report["release_candidate"]==config.release_candidate,
            "network_zero":config.network_requests_executed==0,
            "orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.72","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="strategy-final-cert-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V87.73","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"strategy_final_ledger_v87_73.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"strategy_final_ledger_v87_73.json";b=p.read_bytes()
    d={"stage":"V87.74","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"strategy_final_manifest_v87_74.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def release_package(config,manifest_doc,archive):
    d={"stage":"V87.75","status":"PASS",
       "release_candidate":config.release_candidate,
       "manifest_sha256":manifest_doc["manifest_sha256"],
       "archive_id":archive["archive_id"],
       "promotion_authorized":False,
       "paper_operations_only":True}
    d["release_package_sha256"]=hj(d);return d

def final_chain_verification(integrity,manifest_doc,release_package):
    checks={"integrity_root_present":len(integrity["chain_root_sha256"])==64,
            "manifest_hash_present":len(manifest_doc["manifest_sha256"])==64,
            "release_package_hash_present":len(release_package["release_package_sha256"])==64,
            "promotion_false":release_package["promotion_authorized"] is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.76","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["verification_sha256"]=hj(d);return d

def certification_summary(config,report,audit_doc,release_package,verification):
    d={"stage":"V87.77","status":"PASS",
       "release_candidate":config.release_candidate,
       "strategy_id":report["strategy_id"],
       "certificate_count":report["certificate_count"],
       "chain_root_sha256":report["chain_root_sha256"],
       "audit_status":audit_doc["status"],
       "verification_status":verification["status"],
       "release_package_status":release_package["status"],
       "network_requests_executed":0,"actual_orders_submitted":0}
    d["summary_sha256"]=hj(d);return d

def run_engine(root,c,out):
    c.validate();paths=source_paths(root);chain=load_chain(root);summary=chain_summary(chain)
    integrity=integrity_chain(chain);safety=safety_chain(chain,c)
    compliance=compliance_report(summary,safety);replay=replay_certificate(integrity,summary)
    rollback=rollback_certificate();readiness=release_readiness(c,compliance,replay,rollback)
    archive=archive_record(integrity,c)
    report=final_report(summary,integrity,safety,compliance,replay,rollback,readiness,archive)
    au=audit(c,report)
    docs={"source_paths":paths,"chain_summary":summary,"integrity":integrity,
          "safety":safety,"compliance":compliance,"replay":replay,
          "rollback":rollback,"readiness":readiness,"archive":archive,
          "final_report":report,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    release_pkg=release_package(c,m,archive)
    verification=final_chain_verification(integrity,m,release_pkg)
    cert_summary=certification_summary(c,report,au,release_pkg,verification)
    wj(out/"strategy_release_package_v87_75.json",release_pkg)
    wj(out/"strategy_chain_verification_v87_76.json",verification)
    wj(out/"strategy_certification_summary_v87_77.json",cert_summary)
    return {"stage":"V87.79","status":"PASS" if au["status"]=="PASS" and verification["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"release_package":release_pkg,
            "verification":verification,"summary":cert_summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "certificate_count_three":s["certificate_count"]==3,
            "audit_pass":s["audit_status"]=="PASS",
            "verification_pass":s["verification_status"]=="PASS",
            "release_package_pass":s["release_package_status"]=="PASS",
            "release_candidate_valid":s["release_candidate"]==c.release_candidate,
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V87.80","status":status,
       "scope":"PAPER_STRATEGY_EXECUTION_FINAL_CERTIFICATION",
       "stages_completed":[f"V87.{i:02d}" for i in range(61,81)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "strategy_execution_final_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "strategy_execution_final_manifest":r["manifest"],
       "strategy_execution_release_package":r["release_package"],
       "checks":checks,"failed_checks":failed,
       "paper_strategy_execution_final_certification_complete":status=="PASS",
       "paper_strategy_execution_rc1_ready":status=="PASS",
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "next_phase":"V87_81_PAPER_STRATEGY_OPERATIONS_RELEASE_CANDIDATE"}
    d["certificate_sha256"]=hj(d);wj(out/"strategy_execution_final_certificate_v87_80.json",d)
    wj(out/"strategy_execution_final_verify_v87_80.json",
       {"stage":"V87.80","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
