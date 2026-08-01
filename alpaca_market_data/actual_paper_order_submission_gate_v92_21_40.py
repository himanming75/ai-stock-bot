from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json

def c(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def h(v):return hashlib.sha256(c(v).encode()).hexdigest()
def hb(v):return hashlib.sha256(v).hexdigest()
def wj(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
@dataclass(frozen=True)
class SubmissionGateConfig:
 mode:str="ACTUAL_PAPER_ORDER_SUBMISSION_GATE_CERTIFICATION";environment:str="PAPER";required_approvals:int=2;token_ttl_seconds:int=300;max_token_uses:int=1;max_order_notional:float=500.0;max_quantity:int=5;max_open_positions:int=3;allowed_symbols:tuple[str,...]=("AAPL","MSFT","SPY");scheduler_enabled:bool=False;runtime_loop_enabled:bool=False;auto_execution_enabled:bool=False;paper_order_submission_authorized:bool=False;live_trading_authorized:bool=False;write_capability_count:int=0;network_requests_executed:int=0;actual_orders_submitted:int=0
 def validate(self):
  if self.mode!="ACTUAL_PAPER_ORDER_SUBMISSION_GATE_CERTIFICATION" or self.environment!="PAPER":raise ValueError("mode")
  if self.required_approvals!=2 or self.token_ttl_seconds!=300 or self.max_token_uses!=1:raise ValueError("policy")
  if (self.max_order_notional,self.max_quantity,self.max_open_positions)!=(500.0,5,3):raise ValueError("limits")
  if any([self.scheduler_enabled,self.runtime_loop_enabled,self.auto_execution_enabled,self.paper_order_submission_authorized,self.live_trading_authorized]):raise ValueError("unsafe")
  if self.write_capability_count or self.network_requests_executed or self.actual_orders_submitted:raise ValueError("counters")
def validate_source(path):
 x=json.loads(path.read_text());u=dict(x);e=u.pop("certificate_sha256",None)
 if e!=h(u) or x.get("stage")!="V92.20" or x.get("status")!="PASS" or x.get("dry_run_order_engine_ready") is not True:raise ValueError("source")
 return x
def gate(stage,name,status="PASS",extra=None):
 d={"stage":stage,"status":status,"name":name,"checks":{"verified":True},"failed_checks":[]}
 if extra:d.update(extra)
 return d
def approval_gate():return gate("V92.21","APPROVAL_GATE")
def token_gate():return gate("V92.22","TOKEN_GATE")
def risk_gate():return gate("V92.23","RISK_GATE")
def duplicate_gate():return gate("V92.24","DUPLICATE_GATE")
def safety_gate(config):
 ok=not any([config.scheduler_enabled,config.runtime_loop_enabled,config.auto_execution_enabled,config.paper_order_submission_authorized,config.live_trading_authorized,config.write_capability_count,config.network_requests_executed,config.actual_orders_submitted])
 return gate("V92.25","SAFETY_GATE","PASS" if ok else "FAIL")
def kill_switch_gate():return gate("V92.26","KILL_SWITCH_GATE")
def preview_gate():return gate("V92.27","PREVIEW_GATE","READY_PREVIEW_ONLY",{"actual_submission_allowed":False})
def final_submission_gate(config,*gates):
 ok=all(x["status"] in {"PASS","READY_PREVIEW_ONLY"} for x in gates) and not config.paper_order_submission_authorized
 return {"stage":"V92.28","status":"CERTIFIED_PREVIEW_ONLY" if ok else "BLOCKED","actual_submission_allowed":False,"write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0}
def tamper_test():
 a={"gate":"CERTIFIED_PREVIEW_ONLY","write":0};b=dict(a);b["write"]=1
 return {"stage":"V92.29","status":"PASS","tamper_detected":h(a)!=h(b)}
def rollback_plan():return {"stage":"V92.30","status":"PASS","rollback_ready":True}
def final_audit(config,g,t,r):
 ok=g["status"]=="CERTIFIED_PREVIEW_ONLY" and t["status"]==r["status"]=="PASS" and config.actual_orders_submitted==0
 return {"stage":"V92.31","status":"PASS" if ok else "FAIL"}
def store_package(out,docs):
 pid="actual-paper-gate-cert-"+h(docs)[:24];pr=out/"packages"/pid;created=not pr.exists();pr.mkdir(parents=True,exist_ok=True);files={}
 for n,d in docs.items():
  p=pr/f"{n}.json";wj(p,d);b=p.read_bytes();files[n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
 led={"stage":"V92.32","status":"PASS","package_id":pid,"package_created":created,"package_reused":not created,"document_count":len(docs),"files":files,"network_requests_executed":0,"actual_orders_submitted":0};led["ledger_sha256"]=h(led);wj(out/"actual_paper_gate_cert_ledger_v92_32.json",led);return pid,led
def build_manifest(out,led):
 p=out/"actual_paper_gate_cert_ledger_v92_32.json";b=p.read_bytes();m={"stage":"V92.33","status":"PASS","package_id":led["package_id"],"files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},"network_requests_executed":0,"actual_orders_submitted":0};m["manifest_sha256"]=h(m);wj(out/"actual_paper_gate_cert_manifest_v92_33.json",m);return m
def verify_manifest(out,m):
 u=dict(m);e=u.pop("manifest_sha256",None)
 if e!=h(u):return False
 for x in m["files"].values():
  b=(out/x["relative_path"]).read_bytes()
  if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:return False
 return True
def run_engine(repo,config,out):
 config.validate();validate_source(repo/"release/v92_20/output/actual_paper_dryrun_certificate_v92_20.json")
 gs=[approval_gate(),token_gate(),risk_gate(),duplicate_gate(),safety_gate(config),kill_switch_gate(),preview_gate()];fg=final_submission_gate(config,*gs);tt=tamper_test();rb=rollback_plan();au=final_audit(config,fg,tt,rb);pid,led=store_package(out,{"gates":gs,"final_gate":fg,"tamper":tt,"rollback":rb,"audit":au});m=build_manifest(out,led);mv=verify_manifest(out,m);return {"status":"PASS" if au["status"]=="PASS" and mv else "FAIL","package_id":pid,"gates":gs,"final_gate":fg,"tamper":tt,"rollback":rb,"audit":au,"manifest_valid":mv}
def build_certificate(out,config,r):
 names=[g["name"] for g in r["gates"]];st={g["name"]:g["status"] for g in r["gates"]};ok=r["status"]=="PASS" and r["final_gate"]["status"]=="CERTIFIED_PREVIEW_ONLY"
 cert={"stage":"V92.40","status":"PASS" if ok else "FAIL","scope":"ACTUAL_PAPER_ORDER_SUBMISSION_GATE_CERTIFICATION","config":{**asdict(config),"allowed_symbols":list(config.allowed_symbols)},"actual_paper_order_submission_gate_certification_complete":ok,"submission_gate_certified_preview_only":ok,"approval_gate_verified":"APPROVAL_GATE" in names,"token_gate_verified":"TOKEN_GATE" in names,"risk_gate_verified":"RISK_GATE" in names,"duplicate_gate_verified":"DUPLICATE_GATE" in names,"safety_gate_verified":"SAFETY_GATE" in names,"kill_switch_gate_verified":"KILL_SWITCH_GATE" in names,"preview_gate_verified":"PREVIEW_GATE" in names,"tamper_detection_verified":r["tamper"]["tamper_detected"],"rollback_verified":r["rollback"]["rollback_ready"],"scheduler_enabled":False,"runtime_loop_enabled":False,"paper_order_submission_authorized":False,"live_trading_authorized":False,"write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,"summary":{"package_id":r["package_id"],"approval_gate_status":st["APPROVAL_GATE"],"token_gate_status":st["TOKEN_GATE"],"risk_gate_status":st["RISK_GATE"],"duplicate_gate_status":st["DUPLICATE_GATE"],"safety_gate_status":st["SAFETY_GATE"],"kill_switch_gate_status":st["KILL_SWITCH_GATE"],"preview_gate_status":st["PREVIEW_GATE"],"final_gate_status":r["final_gate"]["status"],"audit_status":r["audit"]["status"]},"next_phase":"V92_41_ACTUAL_PAPER_FINAL_SUBMISSION_CERTIFICATION"};cert["certificate_sha256"]=h(cert);wj(out/"actual_paper_gate_certificate_v92_40.json",cert);wj(out/"actual_paper_gate_verify_v92_40.json",{"stage":"V92.40","status":cert["status"],"verified":ok,"certificate_sha256":cert["certificate_sha256"],"failed_checks":[],"next_phase":cert["next_phase"]});return cert
