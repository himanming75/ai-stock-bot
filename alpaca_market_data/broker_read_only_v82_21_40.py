from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class BrokerReadOnlyConfig:
    mode:str="READ_ONLY_OFFLINE_FIXTURE"
    provider:str="ALPACA_COMPATIBLE"
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="READ_ONLY_OFFLINE_FIXTURE": raise ValueError("safe mode")
        if self.provider!="ALPACA_COMPATIBLE": raise ValueError("provider")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("read only offline")

def validate_live_safety_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V82.20" or c.get("status")!="PASS": raise ValueError("bad V82.20 certificate")
    if c.get("live_safety_foundation_complete") is not True or c.get("live_trading_authorized") is not False:
        raise ValueError("safety prerequisite")
    return c

def capability_contract()->dict[str,Any]:
    caps={
      "account_read":True,"positions_read":True,"orders_read":True,"clock_read":True,"assets_read":True,
      "market_data_read":True,"order_submit":False,"order_cancel":False,"order_replace":False,
      "position_close":False,"account_transfer":False
    }
    d={"stage":"V82.21","status":"PASS","capabilities":caps,
       "read_capability_count":sum(v for k,v in caps.items() if k.endswith("_read")),
       "write_capability_count":sum(v for k,v in caps.items() if not k.endswith("_read"))}
    d["contract_sha256"]=hj(d);return d

def account_fixture()->dict[str,Any]:
    d={"stage":"V82.22","account_id":"fixture-paper-account","status":"ACTIVE","currency":"USD",
       "cash":25000.0,"equity":100000.0,"buying_power":50000.0,"pattern_day_trader":False,
       "source":"OFFLINE_FIXTURE"}
    d["account_sha256"]=hj(d);return d

def positions_fixture()->list[dict[str,Any]]:
    rows=[
      {"symbol":"AAPL","quantity":80,"average_entry_price":180.0,"market_price":190.0,"market_value":15200.0},
      {"symbol":"MSFT","quantity":20,"average_entry_price":400.0,"market_price":420.0,"market_value":8400.0},
      {"symbol":"SPY","quantity":50,"average_entry_price":530.0,"market_price":550.0,"market_value":27500.0},
    ]
    out=[]
    for r in rows:
        x={"stage":"V82.23",**r,"source":"OFFLINE_FIXTURE"};x["position_sha256"]=hj(x);out.append(x)
    return out

def orders_fixture()->list[dict[str,Any]]:
    rows=[
      {"order_id":"ord-001","symbol":"AAPL","side":"BUY","quantity":10,"status":"FILLED"},
      {"order_id":"ord-002","symbol":"MSFT","side":"SELL","quantity":5,"status":"CANCELED"},
    ]
    out=[]
    for r in rows:
        x={"stage":"V82.24",**r,"source":"OFFLINE_FIXTURE"};x["order_sha256"]=hj(x);out.append(x)
    return out

def clock_fixture()->dict[str,Any]:
    d={"stage":"V82.25","is_open":False,"timestamp":"2026-07-31T15:30:00-07:00",
       "next_open":"2026-08-03T06:30:00-07:00","next_close":"2026-08-03T13:00:00-07:00",
       "source":"OFFLINE_FIXTURE"}
    d["clock_sha256"]=hj(d);return d

def assets_fixture()->list[dict[str,Any]]:
    rows=[
      {"symbol":"AAPL","tradable":True,"fractionable":True,"shortable":True},
      {"symbol":"MSFT","tradable":True,"fractionable":True,"shortable":True},
      {"symbol":"SPY","tradable":True,"fractionable":True,"shortable":True},
    ]
    out=[]
    for r in rows:
        x={"stage":"V82.26",**r,"source":"OFFLINE_FIXTURE"};x["asset_sha256"]=hj(x);out.append(x)
    return out

def market_data_fixture()->list[dict[str,Any]]:
    rows=[
      {"symbol":"AAPL","bid":189.95,"ask":190.05,"last":190.0},
      {"symbol":"MSFT","bid":419.9,"ask":420.1,"last":420.0},
      {"symbol":"SPY","bid":549.95,"ask":550.05,"last":550.0},
    ]
    out=[]
    for r in rows:
        x={"stage":"V82.27",**r,"source":"OFFLINE_FIXTURE"};x["quote_sha256"]=hj(x);out.append(x)
    return out

def validate_account(a):
    checks={"status_active":a.get("status")=="ACTIVE","cash_nonnegative":a.get("cash", -1)>=0,
      "equity_positive":a.get("equity",0)>0,"buying_power_nonnegative":a.get("buying_power",-1)>=0,
      "source_fixture":a.get("source")=="OFFLINE_FIXTURE"}
    return _result("V82.28",checks)

def validate_positions(rows):
    checks={"positive_count":len(rows)>0,"symbols_unique":len({x["symbol"] for x in rows})==len(rows),
      "quantities_nonnegative":all(x["quantity"]>=0 for x in rows),
      "market_values_consistent":all(abs(x["quantity"]*x["market_price"]-x["market_value"])<1e-8 for x in rows)}
    return _result("V82.29",checks)

def validate_orders(rows):
    allowed={"NEW","ACCEPTED","PARTIALLY_FILLED","FILLED","CANCELED","REJECTED"}
    checks={"positive_count":len(rows)>0,"order_ids_unique":len({x["order_id"] for x in rows})==len(rows),
      "statuses_valid":all(x["status"] in allowed for x in rows),"quantities_positive":all(x["quantity"]>0 for x in rows)}
    return _result("V82.30",checks)

def validate_clock(c):
    return _result("V82.31",{"boolean_open":isinstance(c.get("is_open"),bool),"timestamp_present":bool(c.get("timestamp")),
      "next_open_present":bool(c.get("next_open")),"next_close_present":bool(c.get("next_close"))})

def validate_assets(rows):
    return _result("V82.32",{"positive_count":len(rows)>0,"symbols_unique":len({x["symbol"] for x in rows})==len(rows),
      "tradable_boolean":all(isinstance(x["tradable"],bool) for x in rows)})

def validate_market_data(rows):
    return _result("V82.33",{"positive_count":len(rows)>0,"symbols_unique":len({x["symbol"] for x in rows})==len(rows),
      "bid_ask_valid":all(x["bid"]>0 and x["ask"]>=x["bid"] for x in rows),
      "last_positive":all(x["last"]>0 for x in rows)})

def _result(stage,checks):
    failed=[k for k,v in checks.items() if not v]
    d={"stage":stage,"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["validation_sha256"]=hj(d);return d

def reconcile(account,positions,quotes):
    q={x["symbol"]:x["last"] for x in quotes}
    position_value=sum(x["quantity"]*q[x["symbol"]] for x in positions)
    implied_equity=account["cash"]+position_value
    d={"stage":"V82.34","position_market_value":round(position_value,8),
       "implied_equity":round(implied_equity,8),"reported_equity":account["equity"],
       "difference":round(account["equity"]-implied_equity,8),
       "reconciliation_informational_only":True}
    d["reconciliation_sha256"]=hj(d);return d

def sync_health(validations):
    failed=[x["stage"] for x in validations if x["status"]!="PASS"]
    d={"stage":"V82.35","status":"PASS" if not failed else "FAIL",
       "validation_count":len(validations),"failed_validation_stages":failed,
       "read_only_sync_healthy":not failed,"network_requests_executed":0}
    d["health_sha256"]=hj(d);return d

def build_audit(config,contract,health):
    checks={"config_safe":config.mode=="READ_ONLY_OFFLINE_FIXTURE",
      "read_capabilities_positive":contract["read_capability_count"]>0,
      "write_capabilities_zero":contract["write_capability_count"]==0,
      "sync_health_pass":health["status"]=="PASS",
      "network_zero":health["network_requests_executed"]==0,
      "actual_orders_zero":config.actual_orders_submitted==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V82.36","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    pid="broker-read-only-"+hj(docs)[:24];pdir=out/"packages"/pid;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V82.37","status":"PASS","package_id":pid,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"broker_read_only_master_ledger_v82_37.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"broker_read_only_master_ledger_v82_37.json";b=lp.read_bytes()
    d={"stage":"V82.38","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"broker_read_only_manifest_v82_38.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"broker_read_only_master_ledger_v82_37.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_live_safety_certificate(root/"release/v82_20/output/live_safety_foundation_certificate_v82_20.json")
    contract=capability_contract();account=account_fixture();positions=positions_fixture();orders=orders_fixture()
    clock=clock_fixture();assets=assets_fixture();quotes=market_data_fixture()
    validations=[validate_account(account),validate_positions(positions),validate_orders(orders),
      validate_clock(clock),validate_assets(assets),validate_market_data(quotes)]
    reconciliation=reconcile(account,positions,quotes);health=sync_health(validations);audit=build_audit(c,contract,health)
    docs={"capability_contract":contract,"account":account,"positions":positions,"orders":orders,"clock":clock,
      "assets":assets,"market_data":quotes,"validations":validations,"reconciliation":reconciliation,
      "sync_health":health,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"provider":c.provider,"read_capability_count":contract["read_capability_count"],
      "write_capability_count":contract["write_capability_count"],"account_count":1,
      "position_count":len(positions),"order_count":len(orders),"asset_count":len(assets),
      "quote_count":len(quotes),"market_open":clock["is_open"],"sync_health_status":health["status"],
      "audit_status":audit["status"],"source_live_safety_complete":source["live_safety_foundation_complete"]}
    return {"stage":"V82.39","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v82_20_certificate_present":(root/"release/v82_20/output/live_safety_foundation_certificate_v82_20.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","read_capabilities_positive":s["read_capability_count"]>0,
      "write_capabilities_zero":s["write_capability_count"]==0,"account_one":s["account_count"]==1,
      "positions_positive":s["position_count"]>0,"orders_positive":s["order_count"]>0,
      "assets_positive":s["asset_count"]>0,"quotes_positive":s["quote_count"]>0,
      "sync_health_pass":s["sync_health_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V82.40","status":status,"scope":"OFFLINE_BROKER_READ_ONLY_INTEGRATION_FOUNDATION",
      "stages_completed":[f"V82.{i:02d}" for i in range(21,41)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"broker_read_only_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "broker_read_only_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
      "actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,
      "broker_read_only_foundation_complete":status=="PASS","next_phase":"V82_41_BROKER_CONNECTION_VALIDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"broker_read_only_foundation_certificate_v82_40.json",cert)
    wj(out/"broker_read_only_foundation_verify_v82_40.json",{"stage":"V82.40","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert
