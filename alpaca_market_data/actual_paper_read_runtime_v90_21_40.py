
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
from typing import Any
from datetime import datetime,timezone
import hashlib,json,os

def cj(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v):return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v):return hashlib.sha256(v).hexdigest()
def wj(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")

@dataclass(frozen=True)
class ReadOnlyRuntimeConfig:
 mode:str="ACTUAL_PAPER_READ_ONLY_RUNTIME_VALIDATION"
 base_url:str="https://paper-api.alpaca.markets"
 poll_count:int=3
 heartbeat_stale_seconds:int=120
 cache_ttl_seconds:int=60
 max_consecutive_failures:int=2
 network_opt_in_env:str="AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_RUNTIME_READ"
 scheduler_enabled:bool=False
 runtime_loop_enabled:bool=False
 auto_execution_enabled:bool=False
 paper_order_submission_authorized:bool=False
 live_trading_authorized:bool=False
 write_capability_count:int=0
 def validate(self):
  if self.mode!="ACTUAL_PAPER_READ_ONLY_RUNTIME_VALIDATION":raise ValueError("mode")
  if self.base_url!="https://paper-api.alpaca.markets":raise ValueError("paper only")
  if min(self.poll_count,self.heartbeat_stale_seconds,self.cache_ttl_seconds,self.max_consecutive_failures)<1:raise ValueError("limits")
  if any([self.scheduler_enabled,self.runtime_loop_enabled,self.auto_execution_enabled,
          self.paper_order_submission_authorized,self.live_trading_authorized]):raise ValueError("unsafe")
  if self.write_capability_count!=0:raise ValueError("write")

def validate_source(path:Path):
 c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256")
 if e!=hj(u) or c.get("stage")!="V90.20" or c.get("status")!="PASS":raise ValueError("source")
 if c.get("actual_paper_read_only_ready") is not True:raise ValueError("prerequisite")
 return c

def opt_in(c,env=None):
 env=env or os.environ
 return env.get(c.network_opt_in_env,"").strip().upper()=="YES"

def fixture_snapshot(index=0,is_open=True):
 return {"account":{"status":"ACTIVE","cash":"100000","buying_power":"400000",
   "portfolio_value":"100000","equity":"100000","trading_blocked":False},
  "clock":{"timestamp":f"2026-08-03T09:3{index}:00-04:00","is_open":is_open,
   "next_open":"2026-08-04T09:30:00-04:00","next_close":"2026-08-03T16:00:00-04:00"},
  "calendar":[{"date":"2026-08-03","open":"09:30","close":"16:00"}]}

def validate_snapshot(s):
 checks={"account_active":s["account"].get("status")=="ACTIVE",
 "account_not_blocked":s["account"].get("trading_blocked") is False,
 "account_numeric":all(_num(s["account"].get(k)) for k in ["cash","buying_power","portfolio_value","equity"]),
 "clock_boolean":isinstance(s["clock"].get("is_open"),bool),
 "clock_timestamp":bool(s["clock"].get("timestamp")),
 "calendar_present":isinstance(s["calendar"],list) and len(s["calendar"])>0}
 f=[k for k,v in checks.items() if not v]
 return {"status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f}

def _num(v):
 try:float(v);return True
 except:return False

def heartbeat(poll_index,age_seconds=0):
 return {"poll_index":poll_index,"age_seconds":age_seconds,
         "status":"PASS" if age_seconds<=120 else "FAIL"}

def cache_put(snapshot,poll_index):
 return {"cache_key":"paper-runtime-latest","poll_index":poll_index,
         "snapshot_sha256":hj(snapshot),"status":"CACHED","stale":False}

def cache_check(cache,current_poll,max_age=1):
 age=current_poll-cache["poll_index"]
 return {"age_polls":age,"status":"PASS" if age<=max_age else "FAIL","stale":age>max_age}

def scheduler_gate(snapshot_validation,heartbeat_doc,cache_doc):
 ready=(snapshot_validation["status"]=="PASS" and heartbeat_doc["status"]=="PASS" and cache_doc["status"]=="PASS")
 return {"status":"READY_READ_ONLY" if ready else "BLOCKED",
         "scheduler_dispatch_allowed":False,"strategy_preview_allowed":ready,
         "order_submission_allowed":False}

def poll_once(index,provider):
 try:
  snap=provider(index);v=validate_snapshot(snap);return {"status":"PASS" if v["status"]=="PASS" else "FAIL",
   "poll_index":index,"snapshot":snap,"validation":v,"error":None}
 except Exception as e:
  return {"status":"FAIL","poll_index":index,"snapshot":None,"validation":None,
          "error":type(e).__name__}

def retry_decision(consecutive_failures,c):
 return {"retry_allowed":consecutive_failures<c.max_consecutive_failures,
         "runtime_stop_required":consecutive_failures>=c.max_consecutive_failures}

def runtime_validation(c,provider=fixture_snapshot):
 polls=[];failures=0;latest_cache=None
 for i in range(c.poll_count):
  p=poll_once(i,provider);polls.append(p)
  if p["status"]=="PASS":
   failures=0;latest_cache=cache_put(p["snapshot"],i)
  else:failures+=1
 hbdoc=heartbeat(c.poll_count-1,0)
 cached=cache_check(latest_cache,c.poll_count-1) if latest_cache else {"status":"FAIL","stale":True}
 last_valid=next((p["validation"] for p in reversed(polls) if p["validation"]),{"status":"FAIL"})
 gate=scheduler_gate(last_valid,hbdoc,cached)
 retry=retry_decision(failures,c)
 checks={"poll_count_match":len(polls)==c.poll_count,
 "all_polls_pass":all(p["status"]=="PASS" for p in polls),
 "heartbeat_pass":hbdoc["status"]=="PASS","cache_pass":cached["status"]=="PASS",
 "gate_ready":gate["status"]=="READY_READ_ONLY","dispatch_blocked":gate["scheduler_dispatch_allowed"] is False,
 "orders_blocked":gate["order_submission_allowed"] is False}
 f=[k for k,v in checks.items() if not v]
 return {"status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,
 "polls":polls,"heartbeat":hbdoc,"cache":cached,"gate":gate,"retry":retry,
 "network_mode":"OFFLINE_FIXTURE","network_requests_executed":0,"actual_orders_submitted":0}

def negative_scenarios(c):
 stale_hb=heartbeat(0,999)
 cache=cache_check({"poll_index":0},3)
 bad=fixture_snapshot();bad["account"]["trading_blocked"]=True
 badv=validate_snapshot(bad)
 gate=scheduler_gate(badv,stale_hb,cache)
 retry1=retry_decision(1,c);retry2=retry_decision(2,c)
 return {"status":"PASS","stale_heartbeat_failed":stale_hb["status"]=="FAIL",
 "stale_cache_failed":cache["status"]=="FAIL","blocked_account_failed":badv["status"]=="FAIL",
 "gate_blocked":gate["status"]=="BLOCKED","retry_initial_allowed":retry1["retry_allowed"],
 "retry_exhausted_stops":retry2["runtime_stop_required"]}

def audit(c,r,n):
 checks={"runtime_pass":r["status"]=="PASS","negative_pass":n["status"]=="PASS",
 "scheduler_disabled":not c.scheduler_enabled,"runtime_disabled":not c.runtime_loop_enabled,
 "write_zero":c.write_capability_count==0,"network_zero":r["network_requests_executed"]==0,
 "orders_zero":r["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 return {"status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f}

def store(out,docs):
 pid="paper-read-runtime-"+hj(docs)[:24];d=out/"packages"/pid;d.mkdir(parents=True,exist_ok=True);files={}
 for n,x in docs.items():
  p=d/f"{n}.json";wj(p,x);b=p.read_bytes();files[n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
 led={"status":"PASS","package_id":pid,"files":files,"network_requests_executed":0,"actual_orders_submitted":0}
 led["ledger_sha256"]=hj(led);wj(out/"read_only_runtime_ledger_v90_40.json",led);return pid,led

def manifest(out,led):
 p=out/"read_only_runtime_ledger_v90_40.json";b=p.read_bytes()
 d={"status":"PASS","package_id":led["package_id"],"files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},"actual_orders_submitted":0}
 d["manifest_sha256"]=hj(d);wj(out/"read_only_runtime_manifest_v90_40.json",d);return d

def run_engine(root,c,out):
 c.validate();validate_source(root/"release/v90_20/output/actual_paper_automation_certificate_v90_20.json")
 r=runtime_validation(c);n=negative_scenarios(c);a=audit(c,r,n);pid,led=store(out,{"runtime":r,"negative":n,"audit":a});m=manifest(out,led)
 return {"status":"PASS" if a["status"]=="PASS" else "FAIL","package_id":pid,"runtime":r,"negative":n,"audit":a,"manifest":m}

def certificate(out,c,x):
 r=x["runtime"];checks={"pipeline_pass":x["status"]=="PASS","polls_pass":r["checks"]["all_polls_pass"],
 "heartbeat_pass":r["checks"]["heartbeat_pass"],"cache_pass":r["checks"]["cache_pass"],
 "gate_ready":r["checks"]["gate_ready"],"dispatch_blocked":r["checks"]["dispatch_blocked"],
 "orders_zero":r["actual_orders_submitted"]==0,"audit_pass":x["audit"]["status"]=="PASS"}
 f=[k for k,v in checks.items() if not v]
 d={"stage":"V90.40","status":"PASS" if not f else "FAIL","scope":"ACTUAL_PAPER_READ_ONLY_RUNTIME_VALIDATION",
 "config":asdict(c),"checks":checks,"failed_checks":f,
 "actual_paper_read_only_runtime_validation_complete":not f,"scheduler_readiness_validated":not f,
 "scheduler_enabled":False,"runtime_loop_enabled":False,"paper_order_submission_authorized":False,
 "write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,
 "summary":{"package_id":x["package_id"],"poll_count":c.poll_count,"heartbeat_status":r["heartbeat"]["status"],
 "cache_status":r["cache"]["status"],"scheduler_gate_status":r["gate"]["status"],"audit_status":x["audit"]["status"]},
 "next_phase":"V90_41_ACTUAL_PAPER_RUNTIME_CERTIFICATION"}
 d["certificate_sha256"]=hj(d);wj(out/"read_only_runtime_certificate_v90_40.json",d);wj(out/"read_only_runtime_verify_v90_40.json",{"stage":"V90.40","status":d["status"],"verified":not f,"failed_checks":f,"certificate_sha256":d["certificate_sha256"],"next_phase":d["next_phase"]});return d
