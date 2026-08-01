from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, statistics, tempfile

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
class PerformanceConfig:
    periods_per_year:int=252
    risk_free_rate:float=0.0
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.periods_per_year<1: raise ValueError("periods_per_year")
        if not math.isfinite(self.risk_free_rate): raise ValueError("risk_free_rate")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def _validate_cert(path:Path,stage:str)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text()); u=dict(c); e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!=stage or c.get("status")!="PASS": raise ValueError(f"bad {stage} certificate")
    return c

def validate_portfolio_certificate(path:Path): return _validate_cert(path,"V79.80")
def validate_risk_certificate(path:Path): return _validate_cert(path,"V79.85")

def locate_portfolio_data(output:Path,cert:dict[str,Any])->Path:
    sid=cert["portfolio_summary"]["simulation_id"]; p=output/"simulation"/sid/"portfolio_simulation.json"
    if not p.is_file(): raise FileNotFoundError(p)
    return p

def load_portfolio(path:Path)->dict[str,Any]:
    try: x=json.loads(path.read_text())
    except Exception as e: raise ValueError("bad portfolio json") from e
    req={"initial_cash","final_equity","trades","snapshots"}
    if not req.issubset(x): raise ValueError("missing portfolio fields")
    return x

def periodic_returns(snapshots:list[dict[str,Any]])->list[float]:
    values=[float(x["equity"]) for x in snapshots]
    if any(v<=0 or not math.isfinite(v) for v in values): raise ValueError("invalid equity")
    return [values[i]/values[i-1]-1 for i in range(1,len(values))]

def return_metrics(portfolio:dict[str,Any],c:PerformanceConfig)->dict[str,Any]:
    c.validate()
    initial=float(portfolio["initial_cash"]); final=float(portfolio["final_equity"])
    total_return=final/initial-1 if initial else 0.0
    rets=periodic_returns(portfolio.get("snapshots",[]))
    periods=len(rets)
    annualized_return=(1+total_return)**(c.periods_per_year/periods)-1 if periods>0 and total_return>-1 else total_return
    mean_return=statistics.fmean(rets) if rets else 0.0
    volatility=statistics.pstdev(rets)*math.sqrt(c.periods_per_year) if len(rets)>1 else 0.0
    downside=[min(0.0,r) for r in rets]
    downside_vol=(statistics.pstdev(downside)*math.sqrt(c.periods_per_year)) if len(downside)>1 else 0.0
    excess=mean_return-c.risk_free_rate/c.periods_per_year
    sharpe=(excess*c.periods_per_year/volatility) if volatility>0 else 0.0
    sortino=(excess*c.periods_per_year/downside_vol) if downside_vol>0 else 0.0
    peak=None; max_dd=0.0
    for x in portfolio.get("snapshots",[]):
        eq=float(x["equity"]); peak=eq if peak is None else max(peak,eq)
        dd=(peak-eq)/peak if peak else 0.0; max_dd=max(max_dd,dd)
    calmar=annualized_return/max_dd if max_dd>0 else 0.0
    return {"total_return":total_return,"annualized_return":annualized_return,"mean_period_return":mean_return,
            "annualized_volatility":volatility,"annualized_downside_volatility":downside_vol,
            "sharpe_ratio":sharpe,"sortino_ratio":sortino,"calmar_ratio":calmar,
            "max_drawdown_pct":max_dd,"return_observation_count":periods}

def trade_metrics(trades:list[dict[str,Any]])->dict[str,Any]:
    closed=[float(x.get("realized_pnl",0.0)) for x in trades if x.get("side")=="SELL"]
    wins=[x for x in closed if x>0]; losses=[x for x in closed if x<0]; breakeven=[x for x in closed if x==0]
    n=len(closed); gross_profit=sum(wins); gross_loss=abs(sum(losses))
    win_rate=len(wins)/n if n else 0.0; loss_rate=len(losses)/n if n else 0.0
    avg_win=statistics.fmean(wins) if wins else 0.0; avg_loss=statistics.fmean(losses) if losses else 0.0
    profit_factor=gross_profit/gross_loss if gross_loss>0 else (0.0 if gross_profit==0 else gross_profit)
    expectancy=statistics.fmean(closed) if closed else 0.0
    return {"closed_trade_count":n,"winning_trade_count":len(wins),"losing_trade_count":len(losses),
            "breakeven_trade_count":len(breakeven),"win_rate":win_rate,"loss_rate":loss_rate,
            "average_win":avg_win,"average_loss":avg_loss,"gross_profit":gross_profit,
            "gross_loss":gross_loss,"profit_factor":profit_factor,"expectancy":expectancy}

def analyze_performance(portfolio:dict[str,Any],c:PerformanceConfig)->dict[str,Any]:
    rm=return_metrics(portfolio,c); tm=trade_metrics(portfolio.get("trades",[]))
    vals=list(rm.values())+list(tm.values())
    if any(isinstance(v,float) and not math.isfinite(v) for v in vals): raise ValueError("non-finite analytics")
    return {"stage":"V79.88","status":"PASS","return_metrics":rm,"trade_metrics":tm}

def store_performance(out:Path,src:Path,result):
    aid=f"performance-{hb(src.read_bytes())[:16]}-{hj(result)[:12]}"
    ap=out/"analysis"/aid/"historical_performance_analytics.json"; data=(json.dumps(result,indent=2,sort_keys=True)+"\n").encode()
    created=not ap.exists()
    if ap.exists() and ap.read_bytes()!=data: raise ValueError("analytics cache conflict")
    if created: aw(ap,data)
    ledger={"stage":"V79.89","analytics_id":aid,"created":created,"reused_existing_analysis":not created,
            "closed_trade_count":result["trade_metrics"]["closed_trade_count"],
            "total_return":result["return_metrics"]["total_return"],
            "sharpe_ratio":result["return_metrics"]["sharpe_ratio"]}
    ledger["ledger_sha256"]=hj(ledger); lp=out/"historical_performance_ledger.json"; wj(lp,ledger)
    man={"stage":"V79.89","analytics_id":aid,
         "closed_trade_count":result["trade_metrics"]["closed_trade_count"],
         "total_return":result["return_metrics"]["total_return"],
         "max_drawdown_pct":result["return_metrics"]["max_drawdown_pct"],"files":{},
         "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    for n,p in (("analysis",ap),("ledger",lp)):
        b=p.read_bytes(); man["files"][n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    man["manifest_sha256"]=hj(man); wj(out/"historical_performance_manifest_v79_89.json",man)
    return {"analytics_id":aid,"created":created,"reused_existing_analysis":not created,"manifest":man}

def verify_performance_manifest(out:Path,man):
    u=dict(man); e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for info in man["files"].values():
        p=out/info["relative_path"]; b=p.read_bytes()
        if hb(b)!=info["sha256"] or len(b)!=info["byte_size"]: raise ValueError("tamper")
    return True

def run_performance_analytics(portfolio_output:Path,portfolio_cert_path:Path,risk_cert_path:Path,c:PerformanceConfig,out:Path):
    pc=validate_portfolio_certificate(portfolio_cert_path); validate_risk_certificate(risk_cert_path)
    src=locate_portfolio_data(portfolio_output,pc); portfolio=load_portfolio(src)
    result=analyze_performance(portfolio,c); store=store_performance(out,src,result); verify_performance_manifest(out,store["manifest"])
    return {"stage":"V79.89","status":"PASS","analytics":result,**store,
            "source_preserved":src.is_file(),"network_requests_executed":0,"credentials_used":0,
            "trading_client_created":False,"actual_orders_submitted":0}

def build_performance_certificate(root:Path,out:Path,c:PerformanceConfig,result):
    rm=result["analytics"]["return_metrics"]; tm=result["analytics"]["trade_metrics"]
    checks={"v79_80_certificate_present":(root/"release/v79_80/output/historical_portfolio_simulation_certificate_v79_80.json").is_file(),
            "v79_85_certificate_present":(root/"release/v79_85/output/historical_risk_engine_certificate_v79_85.json").is_file(),
            "pipeline_status_pass":result["status"]=="PASS","metrics_finite":all(math.isfinite(float(v)) for v in list(rm.values())+list(tm.values())),
            "source_preserved":result["source_preserved"] is True,"manifest_hash_present":len(result["manifest"].get("manifest_sha256",""))==64,
            "network_requests_zero":result["network_requests_executed"]==0,"credentials_unused":result["credentials_used"]==0,
            "trading_client_not_created":result["trading_client_created"] is False,"actual_orders_zero":result["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]; status="PASS" if not failed else "FAIL"
    cert={"stage":"V79.90","status":status,"scope":"OFFLINE_HISTORICAL_PERFORMANCE_ANALYTICS",
          "stages_completed":["V79.86","V79.87","V79.88","V79.89","V79.90"],
          "passed_stage_count":5 if status=="PASS" else max(0,5-len(failed)),"failed_stage_count":0 if status=="PASS" else len(failed),
          "config":asdict(c),"performance_summary":{"analytics_id":result["analytics_id"],**rm,**tm,
          "cache_created":result["created"],"cache_reused":result["reused_existing_analysis"],"source_preserved":result["source_preserved"]},
          "performance_manifest":result["manifest"],"checks":checks,"failed_checks":failed,
          "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
          "actual_orders_submitted":0,"live_trading_authorized":False,"next_phase":"V79_91_HISTORICAL_WALK_FORWARD_VALIDATION"}
    cert["certificate_sha256"]=hj(cert); cp=out/"historical_performance_analytics_certificate_v79_90.json"; wj(cp,cert)
    wj(out/"historical_performance_analytics_verify_v79_90.json",{"stage":"V79.90","status":status,"verified":not failed,
       "certificate_sha256":cert["certificate_sha256"],"certificate_path":str(cp.relative_to(root)).replace("\\","/"),"failed_checks":failed})
    return cert

sha256_performance_json=hj
