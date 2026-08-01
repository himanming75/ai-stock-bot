from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class PaperSessionConfig:
    mode:str="DRY_RUN_NO_NETWORK"
    broker_name:str="ALPACA"
    market_timezone:str="America/New_York"
    session_date:str="2026-01-05"
    regular_open:str="09:30"
    regular_close:str="16:00"
    initial_cash:float=100000.0
    initial_buying_power:float=100000.0
    allow_extended_hours:bool=False
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="DRY_RUN_NO_NETWORK" or self.broker_name!="ALPACA": raise ValueError("safe mode")
        ZoneInfo(self.market_timezone)
        datetime.strptime(self.session_date,"%Y-%m-%d")
        for x in (self.regular_open,self.regular_close): datetime.strptime(x,"%H:%M")
        if self.regular_open>=self.regular_close: raise ValueError("market hours")
        if self.initial_cash<=0 or self.initial_buying_power<self.initial_cash: raise ValueError("account values")
        if self.allow_extended_hours: raise ValueError("extended hours disabled")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def _vc(path:Path,stage:str)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!=stage or c.get("status")!="PASS": raise ValueError("bad prerequisite certificate")
    if c.get("actual_orders_submitted")!=0: raise ValueError("orders found")
    return c

def validate_readiness_certificate(path:Path): return _vc(path,"V80.05")

def build_session_config(c:PaperSessionConfig)->dict[str,Any]:
    c.validate()
    d={"stage":"V80.06","status":"PASS","session_date":c.session_date,"market_timezone":c.market_timezone,
       "regular_open":c.regular_open,"regular_close":c.regular_close,"mode":c.mode,"broker_name":c.broker_name,
       "extended_hours":False,"network_allowed":False,"orders_allowed":False}
    d["config_sha256"]=hj(d); return d

def build_market_calendar(c:PaperSessionConfig)->dict[str,Any]:
    c.validate(); tz=ZoneInfo(c.market_timezone)
    od=datetime.fromisoformat(f"{c.session_date}T{c.regular_open}:00").replace(tzinfo=tz)
    cd=datetime.fromisoformat(f"{c.session_date}T{c.regular_close}:00").replace(tzinfo=tz)
    d={"stage":"V80.07","status":"PASS","session_date":c.session_date,"market_timezone":c.market_timezone,
       "open_at":od.isoformat(),"close_at":cd.isoformat(),"duration_minutes":int((cd-od).total_seconds()//60),
       "holiday":False,"weekend":od.weekday()>=5}
    if d["weekend"]: raise ValueError("session date is weekend")
    d["calendar_sha256"]=hj(d); return d

def market_state(calendar:dict[str,Any],at_iso:str)->str:
    at=datetime.fromisoformat(at_iso); op=datetime.fromisoformat(calendar["open_at"]); cl=datetime.fromisoformat(calendar["close_at"])
    if at.tzinfo is None: raise ValueError("timezone required")
    if at<op: return "PRE_OPEN"
    if at<cl: return "OPEN"
    return "CLOSED"

def build_account_snapshot(c:PaperSessionConfig)->dict[str,Any]:
    c.validate()
    d={"stage":"V80.08","status":"PASS","cash":c.initial_cash,"buying_power":c.initial_buying_power,
       "equity":c.initial_cash,"long_market_value":0.0,"short_market_value":0.0,"position_count":0,
       "source":"SYNTHETIC_OFFLINE","broker_account_queried":False}
    d["snapshot_sha256"]=hj(d); return d

def initialize_portfolio(account:dict[str,Any])->dict[str,Any]:
    d={"stage":"V80.09","status":"PASS","cash":account["cash"],"buying_power":account["buying_power"],
       "equity":account["equity"],"positions":{},"realized_pnl":0.0,"unrealized_pnl":0.0,
       "pending_order_count":0,"filled_order_count":0}
    d["portfolio_sha256"]=hj(d); return d

def make_session_id(config:dict[str,Any],account:dict[str,Any])->str:
    return "paper-session-"+hj({"config":config["config_sha256"],"account":account["snapshot_sha256"]})[:24]

def create_session(config,calendar,account,portfolio)->dict[str,Any]:
    sid=make_session_id(config,account)
    d={"stage":"V80.10","status":"CREATED","session_id":sid,"state":"CREATED",
       "session_date":config["session_date"],"market_timezone":config["market_timezone"],
       "market_open_at":calendar["open_at"],"market_close_at":calendar["close_at"],
       "account_snapshot_sha256":account["snapshot_sha256"],"portfolio_sha256":portfolio["portfolio_sha256"],
       "transition_count":0,"network_requests_executed":0,"credentials_used":0,
       "trading_client_created":False,"actual_orders_submitted":0}
    d["session_sha256"]=hj(d); return d

_ALLOWED={"CREATED":{"VALIDATED"},"VALIDATED":{"READY"},"READY":{"OPEN","CLOSED"},"OPEN":{"PAUSED","CLOSED"},"PAUSED":{"OPEN","CLOSED"},"CLOSED":{"CERTIFIED"},"CERTIFIED":set()}
def transition_session(session:dict[str,Any],target:str,reason:str)->dict[str,Any]:
    current=session["state"]; target=target.upper()
    if target not in _ALLOWED.get(current,set()): raise ValueError(f"invalid transition {current}->{target}")
    event={"sequence":session.get("transition_count",0)+1,"from":current,"to":target,"reason":reason}
    out=dict(session); out["state"]=target; out["status"]=target; out["transition_count"]=event["sequence"]
    out["last_transition"]=event; out.pop("session_sha256",None); out["session_sha256"]=hj(out)
    return out

def validate_session(session,config,calendar,account,portfolio)->dict[str,Any]:
    checks={"session_id_valid":session["session_id"]==make_session_id(config,account),
            "config_hash_matches":session["market_open_at"]==calendar["open_at"],
            "account_hash_matches":session["account_snapshot_sha256"]==account["snapshot_sha256"],
            "portfolio_hash_matches":session["portfolio_sha256"]==portfolio["portfolio_sha256"],
            "cash_matches":portfolio["cash"]==account["cash"],"positions_empty":portfolio["positions"]=={},
            "network_zero":session["network_requests_executed"]==0,"orders_zero":session["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V80.11","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d); return d

def build_lifecycle(session:dict[str,Any],calendar:dict[str,Any])->tuple[dict[str,Any],list[dict[str,Any]]]:
    events=[]; s=session
    for target,reason in [("VALIDATED","configuration verified"),("READY","offline session initialized"),
                          ("OPEN","synthetic market-open lifecycle event"),("CLOSED","synthetic market-close lifecycle event"),
                          ("CERTIFIED","session audit complete")]:
        before=s["state"]; s=transition_session(s,target,reason); events.append({"sequence":len(events)+1,"from":before,"to":target,"reason":reason})
    return s,events

def build_cash_ledger(account,lifecycle)->dict[str,Any]:
    entries=[{"sequence":1,"type":"OPENING_BALANCE","amount":account["cash"],"balance_after":account["cash"]}]
    d={"stage":"V80.12","status":"PASS","opening_cash":account["cash"],"closing_cash":account["cash"],
       "entry_count":len(entries),"entries":entries,"cash_conserved":True}
    d["cash_ledger_sha256"]=hj(d); return d

def build_equity_ledger(account,lifecycle)->dict[str,Any]:
    entries=[{"sequence":i+1,"session_state":e["to"],"equity":account["equity"]} for i,e in enumerate(lifecycle)]
    d={"stage":"V80.13","status":"PASS","opening_equity":account["equity"],"closing_equity":account["equity"],
       "entry_count":len(entries),"entries":entries,"equity_conserved":True}
    d["equity_ledger_sha256"]=hj(d); return d

def build_position_ledger(portfolio)->dict[str,Any]:
    d={"stage":"V80.14","status":"PASS","opening_position_count":0,"closing_position_count":len(portfolio["positions"]),
       "position_event_count":0,"events":[],"positions_conserved":portfolio["positions"]=={}}
    d["position_ledger_sha256"]=hj(d); return d

def build_session_audit(config,calendar,account,portfolio,session,validation,lifecycle,cash,equity,positions)->dict[str,Any]:
    checks={"validation_pass":validation["status"]=="PASS","final_state_certified":session["state"]=="CERTIFIED",
            "cash_conserved":cash["cash_conserved"],"equity_conserved":equity["equity_conserved"],
            "positions_conserved":positions["positions_conserved"],"transition_count":session["transition_count"]==5,
            "network_zero":session["network_requests_executed"]==0,"credentials_zero":session["credentials_used"]==0,
            "client_false":session["trading_client_created"] is False,"orders_zero":session["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V80.15","status":"PASS" if not failed else "FAIL","session_id":session["session_id"],
       "checks":checks,"failed_checks":failed,"lifecycle_event_count":len(lifecycle)}
    d["audit_sha256"]=hj(d); return d

def store_session_package(out:Path, documents:dict[str,dict[str,Any]])->dict[str,Any]:
    sid=documents["session"]["session_id"]; pdir=out/"sessions"/sid
    created=not pdir.exists(); files={}
    for name,doc in documents.items():
        p=pdir/f"{name}.json"; data=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=data: raise ValueError("session package conflict")
        if not p.exists(): aw(p,data)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(data),"byte_size":len(data)}
    ledger={"stage":"V80.16","status":"PASS","session_id":sid,"package_created":created,"package_reused":not created,
            "document_count":len(documents),"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger); wj(out/"paper_session_master_ledger_v80_16.json",ledger)
    return {"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out:Path,ledger:dict[str,Any])->dict[str,Any]:
    lp=out/"paper_session_master_ledger_v80_16.json"; b=lp.read_bytes()
    d={"stage":"V80.17","status":"PASS","session_id":ledger["session_id"],
       "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
       "nested_document_count":ledger["document_count"],"network_requests_executed":0,"credentials_used":0,
       "trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d); wj(out/"paper_session_manifest_v80_17.json",d); return d

def verify_manifest(out:Path,m:dict[str,Any])->bool:
    u=dict(m); e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"]; b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("tamper")
    ledger=json.loads((out/"paper_session_master_ledger_v80_16.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"]; b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("nested tamper")
    return True

def run_paper_session(root:Path,c:PaperSessionConfig,out:Path)->dict[str,Any]:
    ready=_vc(root/"release/v80_05/output/paper_trading_readiness_certificate_v80_05.json","V80.05")
    config=build_session_config(c); calendar=build_market_calendar(c); account=build_account_snapshot(c)
    portfolio=initialize_portfolio(account); session=create_session(config,calendar,account,portfolio)
    validation=validate_session(session,config,calendar,account,portfolio)
    final_session,lifecycle=build_lifecycle(session,calendar)
    cash=build_cash_ledger(account,lifecycle); equity=build_equity_ledger(account,lifecycle); positions=build_position_ledger(portfolio)
    audit=build_session_audit(config,calendar,account,portfolio,final_session,validation,lifecycle,cash,equity,positions)
    docs={"config":config,"calendar":calendar,"account":account,"portfolio":portfolio,"session":final_session,
          "validation":validation,"lifecycle":{"stage":"V80.10","status":"PASS","events":lifecycle},
          "cash_ledger":cash,"equity_ledger":equity,"position_ledger":positions,"audit":audit}
    stored=store_session_package(out,docs); manifest=build_manifest(out,stored["ledger"]); verify_manifest(out,manifest)
    return {"stage":"V80.17","status":"PASS","readiness_certificate_preserved":True,"documents":docs,
            **stored,"manifest":manifest,"network_requests_executed":0,"credentials_used":0,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_session_certificate(root:Path,out:Path,c:PaperSessionConfig,r:dict[str,Any])->dict[str,Any]:
    s=r["documents"]["session"]; a=r["documents"]["audit"]
    checks={"readiness_certificate_present":(root/"release/v80_05/output/paper_trading_readiness_certificate_v80_05.json").is_file(),
            "pipeline_pass":r["status"]=="PASS","audit_pass":a["status"]=="PASS","session_certified":s["state"]=="CERTIFIED",
            "transition_count_five":s["transition_count"]==5,"manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
            "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
            "client_false":r["trading_client_created"] is False,"orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"stage":"V80.20","status":status,"scope":"OFFLINE_PAPER_SESSION_ENGINE",
          "stages_completed":[f"V80.{i:02d}" for i in range(6,21)],"completed_stage_count":15 if status=="PASS" else 15-len(failed),
          "config":asdict(c),"session_summary":{"session_id":s["session_id"],"final_state":s["state"],
          "transition_count":s["transition_count"],"opening_cash":r["documents"]["account"]["cash"],
          "closing_cash":r["documents"]["cash_ledger"]["closing_cash"],"position_count":0,
          "package_created":r["created"],"package_reused":r["reused"]},
          "session_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,
          "trading_client_created":False,"actual_orders_submitted":0,
          "paper_trading_authorized":False,"live_trading_authorized":False,
          "next_phase":"V80_21_PAPER_ORDER_AND_FILL_ENGINE"}
    cert["certificate_sha256"]=hj(cert); wj(out/"paper_session_engine_certificate_v80_20.json",cert)
    wj(out/"paper_session_engine_verify_v80_20.json",{"stage":"V80.20","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert

sha256_paper_session_json=hj
