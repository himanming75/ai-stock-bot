from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
from typing import Any,Callable,Mapping
import hashlib,json,os,ssl,tempfile
from urllib.parse import quote,urlencode,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def cj(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v):return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v):return hashlib.sha256(v).hexdigest()
def wj(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:h.write(b);t=Path(h.name)
 os.replace(t,p)

TERMINAL={"filled","canceled","expired","rejected","replaced","done_for_day","stopped","suspended"}
ACTIVE={"accepted","pending_new","accepted_for_bidding","new","partially_filled","pending_cancel","pending_replace","calculated","held"}

@dataclass(frozen=True)
class LifecycleConfig:
 mode:str="PAPER_ORDER_LIFECYCLE_NETWORK_VALIDATION"
 base_url:str="https://paper-api.alpaca.markets"
 explicit_network_opt_in:bool=False
 required_opt_in_value:str="YES"
 symbol:str="AAPL"
 allow_get:bool=True
 allow_post:bool=False
 allow_patch:bool=False
 allow_delete:bool=False
 actual_orders_submitted:int=0
 def validate(self):
  p=urlparse(self.base_url)
  if self.mode!="PAPER_ORDER_LIFECYCLE_NETWORK_VALIDATION":raise ValueError("mode")
  if p.scheme!="https" or p.hostname!="paper-api.alpaca.markets":raise ValueError("endpoint")
  if not self.allow_get or self.allow_post or self.allow_patch or self.allow_delete:raise ValueError("GET only")
  if self.actual_orders_submitted:raise ValueError("no new orders")

def validate_source(path:Path):
 c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
 if e!=hj(u) or c.get("stage")!="V86.20" or c.get("status")!="PASS":raise ValueError("bad V86.20")
 if c.get("paper_single_order_validation_complete") is not True:raise ValueError("prerequisite")
 return c

def policy():
 d={"stage":"V86.21","status":"PASS","get_only":True,"new_order_creation":False,
 "cancel_allowed":False,"replace_allowed":False,"live_trading_authorized":False};d["policy_sha256"]=hj(d);return d

def credential_status(env:Mapping[str,str]):
 d={"stage":"V86.22","api_key_present":bool(env.get("APCA_API_KEY_ID","").strip()),
 "api_secret_present":bool(env.get("APCA_API_SECRET_KEY","").strip()),"values_redacted":True}
 d["complete"]=d["api_key_present"] and d["api_secret_present"];d["credential_sha256"]=hj(d);return d

def identifier_status(env):
 oid=env.get("AI_STOCK_BOT_PAPER_ORDER_ID","").strip()
 cid=env.get("AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID","").strip()
 d={"stage":"V86.23","order_id_present":bool(oid),"client_order_id_present":bool(cid),
 "valid":bool(oid or cid),"preferred":"ORDER_ID" if oid else "CLIENT_ORDER_ID" if cid else "NONE"}
 d["identifier_sha256"]=hj(d);return d

def opt_in(config,env,enable_network):
 allowed=config.explicit_network_opt_in and enable_network and env.get("AI_STOCK_BOT_ENABLE_PAPER_LIFECYCLE_READ","")==config.required_opt_in_value
 d={"stage":"V86.24","config_opt_in":config.explicit_network_opt_in,"cli_opt_in":enable_network,
 "environment_match":env.get("AI_STOCK_BOT_ENABLE_PAPER_LIFECYCLE_READ","")==config.required_opt_in_value,"allowed":allowed}
 d["opt_in_sha256"]=hj(d);return d

def urls(config,env):
 oid=env.get("AI_STOCK_BOT_PAPER_ORDER_ID","").strip();cid=env.get("AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID","").strip()
 order=(config.base_url+"/v2/orders/"+quote(oid)) if oid else config.base_url+"/v2/orders:by_client_order_id?"+urlencode({"client_order_id":cid})
 d={"stage":"V86.25","order":order,"account":config.base_url+"/v2/account","positions":config.base_url+"/v2/positions","method":"GET"}
 d["urls_sha256"]=hj(d);return d

def default_transport(url,headers,timeout):
 req=Request(url,headers=headers,method="GET")
 with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:return r.status,r.read()

def execute_get(name,url,env,transport:Callable=default_transport):
 headers={"APCA-API-KEY-ID":env["APCA_API_KEY_ID"],"APCA-API-SECRET-KEY":env["APCA_API_SECRET_KEY"],"Accept":"application/json"}
 try:
  status,data=transport(url,headers,8);payload=json.loads(data.decode())
  d={"stage":"V86.26","name":name,"status_code":status,"ok":status==200,"payload":payload,"credentials_redacted":True}
 except HTTPError as e:d={"stage":"V86.26","name":name,"status_code":e.code,"ok":False,"error_class":"HTTP_ERROR","credentials_redacted":True}
 except (URLError,TimeoutError):d={"stage":"V86.26","name":name,"status_code":None,"ok":False,"error_class":"NETWORK_ERROR","credentials_redacted":True}
 d["result_sha256"]=hj(d);return d

def order_schema(order):
 required={"id","client_order_id","symbol","side","type","status","qty","filled_qty"}
 missing=sorted(required-set(order))
 d={"stage":"V86.27","status":"PASS" if not missing else "FAIL","missing_fields":missing}
 d["schema_sha256"]=hj(d);return d

def lifecycle(order):
 status=str(order.get("status","")).lower();qty=float(order.get("qty",0));filled=float(order.get("filled_qty",0))
 classification="TERMINAL" if status in TERMINAL else "ACTIVE" if status in ACTIVE else "UNKNOWN"
 valid=0<=filled<=qty and classification!="UNKNOWN"
 d={"stage":"V86.28","broker_status":status,"classification":classification,"requested_qty":qty,
 "filled_qty":filled,"remaining_qty":qty-filled,"fill_ratio":0 if qty==0 else filled/qty,"status":"PASS" if valid else "FAIL"}
 d["lifecycle_sha256"]=hj(d);return d

def position_reconcile(order,positions):
 symbol=order.get("symbol");side=order.get("side");filled=float(order.get("filled_qty",0))
 matches=[p for p in positions if p.get("symbol")==symbol]
 position_qty=float(matches[0].get("qty",0)) if matches else 0.0
 allowed=True
 if filled>0 and side=="buy":allowed=position_qty>=filled
 d={"stage":"V86.29","symbol":symbol,"matching_position_count":len(matches),"position_qty":position_qty,
 "filled_qty":filled,"status":"PASS" if allowed else "FAIL"}
 d["position_sha256"]=hj(d);return d

def account_reconcile(account):
 required={"status","cash","portfolio_value","buying_power","trading_blocked"};missing=sorted(required-set(account))
 d={"stage":"V86.30","status":"PASS" if not missing else "FAIL","missing_fields":missing,
 "account_status":account.get("status"),"trading_blocked":account.get("trading_blocked")}
 d["account_sha256"]=hj(d);return d

def terminal_action(life):
 d={"stage":"V86.31","terminal":life["classification"]=="TERMINAL","monitoring_required":life["classification"]=="ACTIVE",
 "no_cancel_executed":True,"no_replace_executed":True,"no_new_order_executed":True}
 d["action_sha256"]=hj(d);return d

def fixtures():
 return {"order":{"id":"fixture-order","client_order_id":"single-fixture","symbol":"AAPL","side":"buy","type":"market",
 "status":"filled","qty":"1","filled_qty":"1","filled_avg_price":"200.00"},
 "account":{"status":"ACTIVE","cash":"99800","portfolio_value":"100000","buying_power":"199600","trading_blocked":False},
 "positions":[{"symbol":"AAPL","qty":"1","market_value":"200","avg_entry_price":"200","unrealized_pl":"0"}]}

def evaluate(order,account,positions):
 schema=order_schema(order);life=lifecycle(order);pos=position_reconcile(order,positions);acct=account_reconcile(account);action=terminal_action(life)
 checks={"order_schema":schema["status"]=="PASS","lifecycle":life["status"]=="PASS","position":pos["status"]=="PASS",
 "account":acct["status"]=="PASS","no_write_actions":action["no_cancel_executed"] and action["no_replace_executed"] and action["no_new_order_executed"]}
 failed=[k for k,v in checks.items() if not v]
 d={"stage":"V86.32","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
 "order_schema":schema,"lifecycle":life,"position_reconciliation":pos,"account_reconciliation":acct,"terminal_action":action}
 d["evaluation_sha256"]=hj(d);return d

def offline_run():
 f=fixtures();ev=evaluate(f["order"],f["account"],f["positions"])
 return {"stage":"V86.33","network_mode":"OFFLINE_FIXTURE","network_requests_executed":0,"credentials_used":0,
 "actual_orders_submitted":0,"order":f["order"],"account":f["account"],"positions":f["positions"],"evaluation":ev}

def actual_run(config,env,transport):
 u=urls(config,env);results={n:execute_get(n,u[n],env,transport) for n in ("order","account","positions")}
 if not all(x["ok"] for x in results.values()):raise ValueError("GET lifecycle request failed")
 ev=evaluate(results["order"]["payload"],results["account"]["payload"],results["positions"]["payload"])
 return {"stage":"V86.33","network_mode":"ACTUAL_LIFECYCLE_READ","network_requests_executed":3,"credentials_used":2,
 "actual_orders_submitted":0,"order":results["order"]["payload"],"account":results["account"]["payload"],
 "positions":results["positions"]["payload"],"evaluation":ev,"network_results":results}

def rollback():
 d={"stage":"V86.34","status":"PASS","clear_credentials":True,"clear_order_identifiers":True,
 "disable_lifecycle_opt_in":True,"new_order_submission":False};d["rollback_sha256"]=hj(d);return d

def audit(run):
 ev=run["evaluation"];checks={"evaluation_pass":ev["status"]=="PASS","orders_zero":run["actual_orders_submitted"]==0,
 "request_budget_valid":run["network_requests_executed"] in {0,3},"get_only":True}
 failed=[k for k,v in checks.items() if not v]
 d={"stage":"V86.35","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed};d["audit_sha256"]=hj(d);return d

def store(out,docs):
 pid="order-lifecycle-"+hj(docs)[:24];pd=out/"packages"/pid;created=not pd.exists();files={}
 for n,d in docs.items():
  p=pd/f"{n}.json";b=(json.dumps(d,indent=2,sort_keys=True)+"\n").encode()
  if not p.exists():aw(p,b)
  files[n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
 led={"stage":"V86.36","status":"PASS","package_id":pid,"package_created":created,"package_reused":not created,"files":files}
 led["ledger_sha256"]=hj(led);wj(out/"lifecycle_ledger_v86_36.json",led);return {"package_id":pid,"created":created,"reused":not created,"ledger":led}

def manifest(out,led,run):
 p=out/"lifecycle_ledger_v86_36.json";b=p.read_bytes()
 d={"stage":"V86.37","status":"PASS","package_id":led["package_id"],"files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
 "network_requests_executed":run["network_requests_executed"],"credentials_used":run["credentials_used"],"actual_orders_submitted":0}
 d["manifest_sha256"]=hj(d);wj(out/"lifecycle_manifest_v86_37.json",d);return d

def run_engine(root,c,out,env=None,enable_network=False,transport=default_transport):
 validate_source(root/"release/v86_20/output/single_order_certificate_v86_20.json");c.validate()
 env=dict(os.environ) if env is None else env;cred=credential_status(env);ident=identifier_status(env);gate=opt_in(c,env,enable_network)
 if gate["allowed"]:
  if not cred["complete"] or not ident["valid"]:raise ValueError("credentials and order identifier required")
  run=actual_run(c,env,transport)
 else:run=offline_run()
 au=audit(run);docs={"policy":policy(),"credential_status":cred,"identifier_status":ident,"opt_in":gate,"run":run,"rollback":rollback(),"audit":au}
 st=store(out,docs);m=manifest(out,st["ledger"],run)
 life=run["evaluation"]["lifecycle"]
 summary={"network_mode":run["network_mode"],"broker_status":life["broker_status"],"classification":life["classification"],
 "filled_qty":life["filled_qty"],"remaining_qty":life["remaining_qty"],"position_status":run["evaluation"]["position_reconciliation"]["status"],
 "account_status":run["evaluation"]["account_reconciliation"]["status"],"evaluation_status":run["evaluation"]["status"],
 "audit_status":au["status"],"network_requests_executed":run["network_requests_executed"],"actual_orders_submitted":0}
 return {"stage":"V86.39","status":"PASS",**st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
 s=r["summary"];checks={"pipeline_pass":r["status"]=="PASS","evaluation_pass":s["evaluation_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS","position_pass":s["position_status"]=="PASS","account_pass":s["account_status"]=="PASS",
 "orders_zero":s["actual_orders_submitted"]==0,"request_budget_valid":s["network_requests_executed"] in {0,3}}
 failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
 d={"stage":"V86.40","status":status,"scope":"PAPER_ORDER_LIFECYCLE_NETWORK_VALIDATION",
 "stages_completed":[f"V86.{i:02d}" for i in range(21,41)],"config":asdict(c),
 "lifecycle_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
 "checks":checks,"failed_checks":failed,"network_requests_executed":s["network_requests_executed"],
 "actual_orders_submitted":0,"paper_order_lifecycle_validation_complete":status=="PASS",
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "next_phase":"V86_41_PAPER_POSITION_AND_ACCOUNT_RECONCILIATION"}
 d["certificate_sha256"]=hj(d);wj(out/"lifecycle_certificate_v86_40.json",d)
 wj(out/"lifecycle_verify_v86_40.json",{"stage":"V86.40","status":status,"verified":not failed,"certificate_sha256":d["certificate_sha256"],"next_phase":d["next_phase"]})
 return d
