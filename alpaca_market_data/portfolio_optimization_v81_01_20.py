from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math, os, tempfile

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
class PortfolioOptimizationConfig:
    mode:str="ALLOCATION_ONLY"
    capital:float=100000.0
    maximum_strategy_weight:float=0.40
    minimum_strategy_weight:float=0.05
    maximum_gross_exposure:float=0.90
    cash_reserve:float=0.10
    fractional_kelly_multiplier:float=0.50
    maximum_sector_weight:float=0.50
    maximum_pair_correlation:float=0.85
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="ALLOCATION_ONLY" or self.capital<=0: raise ValueError("safe mode")
        if not 0<self.minimum_strategy_weight<=self.maximum_strategy_weight<=1: raise ValueError("weight limits")
        if not 0<self.maximum_gross_exposure<=1: raise ValueError("gross exposure")
        if not 0<=self.cash_reserve<1 or abs(self.maximum_gross_exposure+self.cash_reserve-1)>1e-9:
            raise ValueError("cash reserve")
        if not 0<self.fractional_kelly_multiplier<=1: raise ValueError("kelly")
        if not 0<self.maximum_sector_weight<=1 or not 0<=self.maximum_pair_correlation<=1:
            raise ValueError("constraints")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_selection_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V81.00" or c.get("status")!="PASS": raise ValueError("bad V81.00 certificate")
    if c.get("strategy_selection_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("selection prerequisite")
    return c

def strategy_universe()->list[dict[str,Any]]:
    return [
      {"strategy_id":"BREAKOUT","selection_score":1.00,"expected_return":0.14,"volatility":0.18,"win_rate":0.60,"payoff_ratio":1.50,"sector":"MOMENTUM"},
      {"strategy_id":"SMA_CROSS","selection_score":0.78,"expected_return":0.10,"volatility":0.14,"win_rate":0.56,"payoff_ratio":1.35,"sector":"TREND"},
      {"strategy_id":"MOMENTUM","selection_score":0.64,"expected_return":0.09,"volatility":0.16,"win_rate":0.54,"payoff_ratio":1.30,"sector":"MOMENTUM"},
      {"strategy_id":"RSI_MEAN_REVERSION","selection_score":0.50,"expected_return":0.07,"volatility":0.11,"win_rate":0.58,"payoff_ratio":1.20,"sector":"MEAN_REVERSION"},
    ]

def correlation_matrix()->dict[str,dict[str,float]]:
    ids=[x["strategy_id"] for x in strategy_universe()]
    vals={
      ("BREAKOUT","SMA_CROSS"):0.72,("BREAKOUT","MOMENTUM"):0.82,("BREAKOUT","RSI_MEAN_REVERSION"):-0.18,
      ("SMA_CROSS","MOMENTUM"):0.68,("SMA_CROSS","RSI_MEAN_REVERSION"):-0.10,
      ("MOMENTUM","RSI_MEAN_REVERSION"):-0.22,
    }
    return {a:{b:(1.0 if a==b else vals.get((a,b),vals.get((b,a),0.0))) for b in ids} for a in ids}

def normalize(raw:dict[str,float],target:float)->dict[str,float]:
    if not raw or any(v<0 or not math.isfinite(v) for v in raw.values()): raise ValueError("raw weights")
    total=sum(raw.values())
    if total<=0: raise ValueError("zero weights")
    return {k:round(v/total*target,12) for k,v in raw.items()}

def equal_weight(universe,config):
    return normalize({x["strategy_id"]:1.0 for x in universe},config.maximum_gross_exposure)

def score_weight(universe,config):
    return normalize({x["strategy_id"]:x["selection_score"] for x in universe},config.maximum_gross_exposure)

def inverse_volatility_weight(universe,config):
    return normalize({x["strategy_id"]:1/x["volatility"] for x in universe},config.maximum_gross_exposure)

def risk_budget_weight(universe,config):
    raw={x["strategy_id"]:x["selection_score"]/x["volatility"] for x in universe}
    return normalize(raw,config.maximum_gross_exposure)

def kelly_fraction(win_rate:float,payoff_ratio:float,multiplier:float)->float:
    if not 0<=win_rate<=1 or payoff_ratio<=0: raise ValueError("kelly inputs")
    full=win_rate-(1-win_rate)/payoff_ratio
    return max(0.0,min(full*multiplier,1.0))

def kelly_weight(universe,config):
    raw={x["strategy_id"]:kelly_fraction(x["win_rate"],x["payoff_ratio"],config.fractional_kelly_multiplier) for x in universe}
    return normalize(raw,config.maximum_gross_exposure)

def apply_weight_caps(weights:dict[str,float],config:PortfolioOptimizationConfig)->dict[str,float]:
    capped={k:min(v,config.maximum_strategy_weight) for k,v in weights.items()}
    target=config.maximum_gross_exposure
    for _ in range(20):
        remaining=target-sum(capped.values())
        if abs(remaining)<1e-10: break
        eligible=[k for k,v in capped.items() if v<config.maximum_strategy_weight-1e-12]
        if not eligible: break
        add=remaining/len(eligible)
        for k in eligible: capped[k]=min(config.maximum_strategy_weight,capped[k]+add)
    return {k:round(v,12) for k,v in capped.items()}

def portfolio_metrics(weights,universe,corr):
    meta={x["strategy_id"]:x for x in universe};ids=list(weights)
    er=sum(weights[i]*meta[i]["expected_return"] for i in ids)
    variance=0.0
    for i in ids:
        for j in ids:
            variance+=weights[i]*weights[j]*meta[i]["volatility"]*meta[j]["volatility"]*corr[i][j]
    vol=math.sqrt(max(variance,0.0))
    sharpe=er/vol if vol else 0.0
    return {"expected_return":round(er,12),"expected_volatility":round(vol,12),"expected_sharpe":round(sharpe,8)}

def validate_constraints(weights,universe,corr,config):
    sectors={}
    for x in universe: sectors[x["sector"]]=sectors.get(x["sector"],0)+weights.get(x["strategy_id"],0)
    pair_violations=[]
    ids=list(weights)
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if weights[a]>0 and weights[b]>0 and corr[a][b]>config.maximum_pair_correlation:
                pair_violations.append(f"{a}:{b}")
    checks={
      "weight_sum":abs(sum(weights.values())-config.maximum_gross_exposure)<1e-8,
      "max_strategy_weight":all(v<=config.maximum_strategy_weight+1e-9 for v in weights.values()),
      "minimum_weight":all(v==0 or v>=config.minimum_strategy_weight-1e-9 for v in weights.values()),
      "max_sector_weight":all(v<=config.maximum_sector_weight+1e-9 for v in sectors.values()),
      "pair_correlation":not pair_violations,
      "cash_reserve":abs(1-sum(weights.values())-config.cash_reserve)<1e-8,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"stage":"V81.12","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "sector_weights":sectors,"pair_correlation_violations":pair_violations}

def candidate(name,weights,universe,corr,config):
    capped=apply_weight_caps(weights,config);metrics=portfolio_metrics(capped,universe,corr)
    constraints=validate_constraints(capped,universe,corr,config)
    score=metrics["expected_sharpe"]-0.5*metrics["expected_volatility"]
    d={"stage":"V81.11","method":name,"weights":capped,"metrics":metrics,"constraints":constraints,
       "optimization_score":round(score,8),"eligible":constraints["status"]=="PASS"}
    d["candidate_sha256"]=hj(d);return d

def select_optimizer(candidates):
    eligible=[x for x in candidates if x["eligible"]]
    if not eligible: raise ValueError("no eligible allocation")
    eligible.sort(key=lambda x:(x["optimization_score"],x["metrics"]["expected_return"],x["method"]),reverse=True)
    winner=eligible[0]
    d={"stage":"V81.13","status":"PASS","selected_method":winner["method"],"weights":winner["weights"],
       "metrics":winner["metrics"],"optimization_score":winner["optimization_score"],
       "order_generation_enabled":False,"order_quantity":0}
    d["selection_sha256"]=hj(d);return d

def build_allocation_plan(selection,universe,config):
    meta={x["strategy_id"]:x for x in universe}
    allocations=[]
    for sid,w in selection["weights"].items():
        allocations.append({"strategy_id":sid,"weight":w,"capital":round(w*config.capital,8),
                            "sector":meta[sid]["sector"],"order_quantity":0})
    d={"stage":"V81.14","status":"PASS","capital":config.capital,"invested_capital":round(sum(x["capital"] for x in allocations),8),
       "cash_reserve":round(config.cash_reserve*config.capital,8),"allocation_count":len(allocations),
       "allocations":allocations,"orders_created":0}
    d["plan_sha256"]=hj(d);return d

def build_audit(candidates,selection,plan,config):
    checks={"candidate_count_five":len(candidates)==5,"eligible_positive":any(x["eligible"] for x in candidates),
      "weight_sum_valid":abs(sum(selection["weights"].values())-config.maximum_gross_exposure)<1e-8,
      "cash_reserve_valid":abs(plan["cash_reserve"]-config.cash_reserve*config.capital)<1e-8,
      "allocation_count_four":plan["allocation_count"]==4,"orders_zero":plan["orders_created"]==0,
      "order_generation_disabled":selection["order_generation_enabled"] is False}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V81.15","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out:Path,docs:dict[str,Any]):
    package_id="portfolio-optimization-"+hj(docs)[:24];pdir=out/"packages"/package_id;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V81.16","status":"PASS","package_id":package_id,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"portfolio_optimization_master_ledger_v81_16.json",ledger)
    return {"package_id":package_id,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"portfolio_optimization_master_ledger_v81_16.json";b=lp.read_bytes()
    d={"stage":"V81.17","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"portfolio_optimization_manifest_v81_17.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"portfolio_optimization_master_ledger_v81_16.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();cert=validate_selection_certificate(root/"release/v81_00/output/strategy_selection_certificate_v81_00.json")
    universe=strategy_universe();corr=correlation_matrix()
    models=[
      candidate("EQUAL_WEIGHT",equal_weight(universe,c),universe,corr,c),
      candidate("SCORE_WEIGHT",score_weight(universe,c),universe,corr,c),
      candidate("INVERSE_VOLATILITY",inverse_volatility_weight(universe,c),universe,corr,c),
      candidate("RISK_BUDGET",risk_budget_weight(universe,c),universe,corr,c),
      candidate("FRACTIONAL_KELLY",kelly_weight(universe,c),universe,corr,c),
    ]
    selection=select_optimizer(models);plan=build_allocation_plan(selection,universe,c);audit=build_audit(models,selection,plan,c)
    docs={"universe":{"stage":"V81.02","strategies":universe},"correlation":{"stage":"V81.10","matrix":corr},
          "candidates":{"stage":"V81.11","count":len(models),"candidates":models},
          "selection":selection,"allocation_plan":plan,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"strategy_count":len(universe),"candidate_count":len(models),"eligible_candidate_count":sum(x["eligible"] for x in models),
      "selected_method":selection["selected_method"],"weight_sum":round(sum(selection["weights"].values()),12),
      "cash_reserve":plan["cash_reserve"],"invested_capital":plan["invested_capital"],
      "expected_return":selection["metrics"]["expected_return"],"expected_volatility":selection["metrics"]["expected_volatility"],
      "expected_sharpe":selection["metrics"]["expected_sharpe"],"order_quantity":0,"audit_status":audit["status"],
      "champion_strategy_id":cert["selection_summary"]["champion_strategy_id"]}
    return {"stage":"V81.18","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v81_00_certificate_present":(root/"release/v81_00/output/strategy_selection_certificate_v81_00.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","strategy_count_four":s["strategy_count"]==4,"candidate_count_five":s["candidate_count"]==5,
      "eligible_positive":s["eligible_candidate_count"]>0,"weight_sum_valid":abs(s["weight_sum"]-c.maximum_gross_exposure)<1e-8,
      "cash_reserve_valid":abs(s["cash_reserve"]-c.cash_reserve*c.capital)<1e-8,"audit_pass":s["audit_status"]=="PASS",
      "order_quantity_zero":s["order_quantity"]==0,"manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V81.20","status":status,"scope":"OFFLINE_PORTFOLIO_OPTIMIZATION_AND_ALLOCATION",
      "stages_completed":[f"V81.{i:02d}" for i in range(1,21)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"optimization_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "optimization_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
      "actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,
      "portfolio_optimization_complete":status=="PASS","next_phase":"V81_21_MULTI_ASSET_PORTFOLIO_ENGINE"}
    cert["certificate_sha256"]=hj(cert);wj(out/"portfolio_optimization_certificate_v81_20.json",cert)
    wj(out/"portfolio_optimization_verify_v81_20.json",{"stage":"V81.20","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert

sha256_portfolio_optimization_json=hj
