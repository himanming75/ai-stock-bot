from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

def cj(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode()).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("wb",delete=False,dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class RiskConfig:
    max_position_pct:float=0.20
    max_gross_exposure_pct:float=0.80
    max_open_positions:int=5
    max_drawdown_pct:float=0.20
    risk_per_trade_pct:float=0.01
    stop_loss_pct:float=0.05
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        vals=[self.max_position_pct,self.max_gross_exposure_pct,self.max_drawdown_pct,self.risk_per_trade_pct,self.stop_loss_pct]
        if any(v<=0 or v>1 for v in vals): raise ValueError("risk percentages")
        if self.max_position_pct>self.max_gross_exposure_pct: raise ValueError("position exceeds gross exposure")
        if self.max_open_positions<1: raise ValueError("max positions")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_portfolio_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V79.80" or c.get("status")!="PASS": raise ValueError("bad portfolio certificate")
    return c

def locate_portfolio_data(output:Path,cert:dict[str,Any])->Path:
    sid=cert["portfolio_summary"]["simulation_id"]; p=output/"simulation"/sid/"portfolio_simulation.json"
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def load_portfolio(path:Path)->dict[str,Any]:
    try: x=json.loads(path.read_text())
    except Exception as e: raise ValueError("bad portfolio json") from e
    req={"initial_cash","final_cash","final_equity","positions","trades","snapshots"}
    if not req.issubset(x): raise ValueError("missing portfolio fields")
    return x

def position_size(equity:float,price:float,c:RiskConfig)->dict[str,Any]:
    c.validate()
    if equity<=0 or price<=0: raise ValueError("equity or price")
    risk_budget=equity*c.risk_per_trade_pct
    per_share_risk=price*c.stop_loss_pct
    risk_qty=int(risk_budget//per_share_risk)
    cap_qty=int((equity*c.max_position_pct)//price)
    qty=max(0,min(risk_qty,cap_qty))
    return {"equity":equity,"price":price,"risk_budget":risk_budget,"per_share_risk":per_share_risk,
            "risk_quantity":risk_qty,"cap_quantity":cap_qty,"approved_quantity":qty}

def drawdown_metrics(snapshots:list[dict[str,Any]])->dict[str,Any]:
    peak=None; max_dd=0.0; curve=[]
    for x in snapshots:
        eq=float(x["equity"])
        if eq<0 or not math.isfinite(eq): raise ValueError("invalid equity")
        peak=eq if peak is None else max(peak,eq)
        dd=0.0 if peak==0 else (peak-eq)/peak
        max_dd=max(max_dd,dd)
        curve.append({"timestamp":x["timestamp"],"equity":eq,"peak_equity":peak,"drawdown_pct":dd})
    return {"max_drawdown_pct":max_dd,"drawdown_curve":curve,"observation_count":len(curve)}

def evaluate_risk(portfolio:dict[str,Any],c:RiskConfig)->dict[str,Any]:
    c.validate()
    equity=float(portfolio["final_equity"])
    positions=portfolio.get("positions",{})
    latest={}
    for snap in portfolio.get("snapshots",[]):
        latest=snap
    market_value=float(latest.get("market_value",0.0)) if latest else 0.0
    gross_exposure=0.0 if equity<=0 else market_value/equity
    violations=[]
    if len(positions)>c.max_open_positions: violations.append("MAX_OPEN_POSITIONS")
    if gross_exposure>c.max_gross_exposure_pct+1e-12: violations.append("MAX_GROSS_EXPOSURE")
    dd=drawdown_metrics(portfolio.get("snapshots",[]))
    if dd["max_drawdown_pct"]>c.max_drawdown_pct+1e-12: violations.append("MAX_DRAWDOWN")
    status="PASS" if not violations else "FAIL"
    return {"stage":"V79.83","status":status,"final_equity":equity,"open_position_count":len(positions),
            "gross_exposure_pct":gross_exposure,"max_drawdown_pct":dd["max_drawdown_pct"],
            "violation_count":len(violations),"violations":violations,"drawdown_curve":dd["drawdown_curve"]}

def store_risk(out:Path,src:Path,result):
    rid=f"risk-{hb(src.read_bytes())[:16]}-{hj(result)[:12]}"
    rp=out/"analysis"/rid/"historical_risk_analysis.json"; data=(json.dumps(result,indent=2,sort_keys=True)+"\n").encode()
    created=not rp.exists()
    if rp.exists() and rp.read_bytes()!=data: raise ValueError("risk cache conflict")
    if created: aw(rp,data)
    ledger={"stage":"V79.84","risk_id":rid,"created":created,"reused_existing_analysis":not created,
            "status":result["status"],"violation_count":result["violation_count"],"violations":result["violations"]}
    ledger["ledger_sha256"]=hj(ledger); lp=out/"historical_risk_ledger.json"; wj(lp,ledger)
    man={"stage":"V79.84","risk_id":rid,"status":result["status"],"violation_count":result["violation_count"],
         "max_drawdown_pct":result["max_drawdown_pct"],"gross_exposure_pct":result["gross_exposure_pct"],"files":{},
         "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    for n,p in (("analysis",rp),("ledger",lp)):
        b=p.read_bytes(); man["files"][n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    man["manifest_sha256"]=hj(man); wj(out/"historical_risk_manifest_v79_84.json",man)
    return {"risk_id":rid,"created":created,"reused_existing_analysis":not created,"manifest":man}

def verify_risk_manifest(out:Path,man):
    u=dict(man); e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for info in man["files"].values():
        p=out/info["relative_path"]; b=p.read_bytes()
        if hb(b)!=info["sha256"] or len(b)!=info["byte_size"]: raise ValueError("tamper")
    return True

def run_risk_engine(portfolio_output:Path,certificate_path:Path,c:RiskConfig,out:Path):
    cert=validate_portfolio_certificate(certificate_path); src=locate_portfolio_data(portfolio_output,cert)
    portfolio=load_portfolio(src); result=evaluate_risk(portfolio,c); store=store_risk(out,src,result); verify_risk_manifest(out,store["manifest"])
    return {"stage":"V79.84","status":"PASS","risk_result":result,**store,
            "source_preserved":src.is_file(),"network_requests_executed":0,"credentials_used":0,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_risk_certificate(root:Path,out:Path,c:RiskConfig,result):
    rr=result["risk_result"]
    checks={"v79_80_certificate_present":(root/"release/v79_80/output/historical_portfolio_simulation_certificate_v79_80.json").is_file(),
            "pipeline_status_pass":result["status"]=="PASS","risk_analysis_completed":rr["status"] in {"PASS","FAIL"},
            "violations_zero":rr["violation_count"]==0,"drawdown_within_limit":rr["max_drawdown_pct"]<=c.max_drawdown_pct+1e-12,
            "exposure_within_limit":rr["gross_exposure_pct"]<=c.max_gross_exposure_pct+1e-12,
            "source_preserved":result["source_preserved"] is True,"manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,
            "network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,
            "trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"stage":"V79.85","status":status,"scope":"OFFLINE_HISTORICAL_RISK_ENGINE",
          "stages_completed":["V79.81","V79.82","V79.83","V79.84","V79.85"],
          "passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),
          "config":asdict(c),"risk_summary":{"risk_id":result["risk_id"],"risk_status":rr["status"],"violation_count":rr["violation_count"],
          "open_position_count":rr["open_position_count"],"gross_exposure_pct":rr["gross_exposure_pct"],
          "max_drawdown_pct":rr["max_drawdown_pct"],"cache_created":result["created"],
          "cache_reused":result["reused_existing_analysis"],"source_preserved":result["source_preserved"]},
          "risk_manifest":result["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
          "actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_86_HISTORICAL_PERFORMANCE_ANALYTICS"}
    cert["certificate_sha256"]=hj(cert); cp=out/"historical_risk_engine_certificate_v79_85.json"; wj(cp,cert)
    wj(out/"historical_risk_engine_verify_v79_85.json",{"stage":"V79.85","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(root)).replace("\\","/"),"failed_checks":failed})
    return cert

sha256_risk_json=hj
