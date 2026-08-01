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
class PortfolioConfig:
    initial_cash:float=100000.0
    allocation_per_trade:float=0.10
    commission_per_trade:float=0.0
    allow_short:bool=False
    allow_fractional:bool=False
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.initial_cash<=0: raise ValueError("initial cash")
        if not 0<self.allocation_per_trade<=1: raise ValueError("allocation")
        if self.commission_per_trade<0: raise ValueError("commission")
        if self.allow_short or self.allow_fractional: raise ValueError("long-only whole-share simulation")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_signal_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V79.75" or c.get("status")!="PASS": raise ValueError("bad signal certificate")
    return c

def locate_signal_data(output:Path,cert:dict[str,Any])->Path:
    cid=cert["signal_summary"]["cache_id"]; p=output/"cache"/cid/"historical_signals.jsonl"
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def load_signal_rows(path:Path)->list[dict[str,Any]]:
    out=[]
    for n,line in enumerate(path.read_text().splitlines(),1):
        if not line.strip(): continue
        try: x=json.loads(line)
        except Exception as e: raise ValueError(f"bad line {n}") from e
        if not {"symbol","timeframe","timestamp","source_close","signal"}.issubset(x): raise ValueError("missing fields")
        if x["signal"] not in {"BUY","SELL","HOLD"}: raise ValueError("invalid signal")
        out.append(x)
    if not out: raise ValueError("empty signal input")
    return sorted(out,key=lambda x:(x["timestamp"],x["symbol"]))

def simulate_portfolio(rows:list[dict[str,Any]],c:PortfolioConfig)->dict[str,Any]:
    c.validate(); cash=c.initial_cash; positions={}; avg_cost={}; realized=0.0; trades=[]; snapshots=[]
    latest={}
    for x in rows:
        s=x["symbol"]; px=float(x["source_close"]); latest[s]=px; action=x["signal"]
        if px<=0 or not math.isfinite(px): raise ValueError("invalid price")
        if action=="BUY" and positions.get(s,0)==0:
            budget=min(cash,max(0.0,c.initial_cash*c.allocation_per_trade))
            qty=int((budget-c.commission_per_trade)//px)
            if qty>0:
                cost=qty*px+c.commission_per_trade
                cash-=cost; positions[s]=qty; avg_cost[s]=px
                trades.append({"timestamp":x["timestamp"],"symbol":s,"side":"BUY","quantity":qty,"price":px,"cash_after":cash,"realized_pnl":0.0})
        elif action=="SELL" and positions.get(s,0)>0:
            qty=positions[s]; pnl=qty*(px-avg_cost[s])-c.commission_per_trade
            cash+=qty*px-c.commission_per_trade; realized+=pnl
            trades.append({"timestamp":x["timestamp"],"symbol":s,"side":"SELL","quantity":qty,"price":px,"cash_after":cash,"realized_pnl":pnl})
            positions[s]=0; avg_cost.pop(s,None)
        market_value=sum(qty*latest.get(sym,avg_cost.get(sym,0.0)) for sym,qty in positions.items())
        snapshots.append({"timestamp":x["timestamp"],"cash":cash,"market_value":market_value,
                          "equity":cash+market_value,"open_position_count":sum(1 for q in positions.values() if q>0)})
    final_mv=sum(qty*latest.get(sym,avg_cost.get(sym,0.0)) for sym,qty in positions.items())
    equity=cash+final_mv
    return {"stage":"V79.77","status":"PASS","initial_cash":c.initial_cash,"final_cash":cash,
            "final_market_value":final_mv,"final_equity":equity,"realized_pnl":realized,
            "unrealized_pnl":final_mv-sum(qty*avg_cost.get(sym,0.0) for sym,qty in positions.items()),
            "total_return":equity/c.initial_cash-1,"trade_count":len(trades),
            "open_position_count":sum(1 for q in positions.values() if q>0),
            "positions":{k:v for k,v in positions.items() if v>0},"trades":trades,"snapshots":snapshots}

def validate_simulation(result):
    if result["final_cash"]< -1e-9: raise ValueError("negative cash")
    if not math.isfinite(result["final_equity"]) or not math.isfinite(result["total_return"]): raise ValueError("invalid metrics")
    if result["trade_count"]!=len(result["trades"]): raise ValueError("trade count mismatch")
    return {"trade_count":result["trade_count"],"open_position_count":result["open_position_count"],
            "final_equity":result["final_equity"],"realized_pnl":result["realized_pnl"],
            "unrealized_pnl":result["unrealized_pnl"],"total_return":result["total_return"]}

def store_portfolio(out:Path,src:Path,result,stats):
    sid=f"portfolio-{hb(src.read_bytes())[:16]}-{hj(stats)[:12]}"
    sim_path=out/"simulation"/sid/"portfolio_simulation.json"; ledger_path=out/"portfolio_trade_ledger.json"
    sim_bytes=(json.dumps(result,indent=2,sort_keys=True)+"\n").encode()
    created=not sim_path.exists()
    if sim_path.exists() and sim_path.read_bytes()!=sim_bytes: raise ValueError("simulation conflict")
    if created: aw(sim_path,sim_bytes)
    ledger={"stage":"V79.78","simulation_id":sid,"created":created,"reused_existing_simulation":not created,
            "trade_count":result["trade_count"],"trades":result["trades"]}
    ledger["ledger_sha256"]=hj(ledger); wj(ledger_path,ledger)
    man={"stage":"V79.79","simulation_id":sid,**stats,"files":{},
         "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    for n,p in (("simulation",sim_path),("ledger",ledger_path)):
        b=p.read_bytes(); man["files"][n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    man["manifest_sha256"]=hj(man); wj(out/"historical_portfolio_manifest_v79_79.json",man)
    return {"simulation_id":sid,"created":created,"reused_existing_simulation":not created,"manifest":man}

def verify_portfolio_manifest(out:Path,man):
    u=dict(man); e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for info in man["files"].values():
        p=out/info["relative_path"]; b=p.read_bytes()
        if hb(b)!=info["sha256"] or len(b)!=info["byte_size"]: raise ValueError("tamper")
    return True

def run_portfolio_simulation(signal_output:Path,certificate_path:Path,c:PortfolioConfig,out:Path):
    cert=validate_signal_certificate(certificate_path); src=locate_signal_data(signal_output,cert)
    result=simulate_portfolio(load_signal_rows(src),c); stats=validate_simulation(result)
    store=store_portfolio(out,src,result,stats); verify_portfolio_manifest(out,store["manifest"])
    return {"stage":"V79.79","status":"PASS","simulation":result,"stats":stats,**store,
            "source_preserved":src.is_file(),"network_requests_executed":0,"credentials_used":0,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_portfolio_certificate(root:Path,out:Path,c:PortfolioConfig,result):
    checks={"v79_75_certificate_present":(root/"release/v79_75/output/historical_signal_engine_certificate_v79_75.json").is_file(),
            "pipeline_status_pass":result["status"]=="PASS","final_equity_nonnegative":result["stats"]["final_equity"]>=0,
            "trade_count_matches":result["stats"]["trade_count"]==len(result["simulation"]["trades"]),
            "source_preserved":result["source_preserved"] is True,
            "manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,
            "network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,
            "trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"stage":"V79.80","status":status,"scope":"OFFLINE_HISTORICAL_PORTFOLIO_SIMULATION",
          "stages_completed":["V79.76","V79.77","V79.78","V79.79","V79.80"],
          "passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),
          "config":asdict(c),"portfolio_summary":{"simulation_id":result["simulation_id"],**result["stats"],
          "initial_cash":result["simulation"]["initial_cash"],"final_cash":result["simulation"]["final_cash"],
          "cache_created":result["created"],"cache_reused":result["reused_existing_simulation"],"source_preserved":result["source_preserved"]},
          "portfolio_manifest":result["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
          "actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_81_HISTORICAL_RISK_ENGINE"}
    cert["certificate_sha256"]=hj(cert); cp=out/"historical_portfolio_simulation_certificate_v79_80.json"; wj(cp,cert)
    wj(out/"historical_portfolio_simulation_verify_v79_80.json",{"stage":"V79.80","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(root)).replace("\\","/"),"failed_checks":failed})
    return cert

sha256_portfolio_json=hj
