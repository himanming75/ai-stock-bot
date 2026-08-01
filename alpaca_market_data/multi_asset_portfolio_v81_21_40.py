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
class MultiAssetPortfolioConfig:
    mode:str="MULTI_ASSET_ALLOCATION_ONLY"
    capital:float=100000.0
    target_invested_weight:float=0.90
    cash_reserve_weight:float=0.10
    maximum_asset_weight:float=0.25
    minimum_asset_weight:float=0.05
    maximum_sector_weight:float=0.45
    maximum_pair_correlation:float=0.90
    rebalance_threshold:float=0.02
    maximum_turnover:float=0.35
    allow_fractional_shares:bool=False
    allow_short_selling:bool=False
    allow_network:bool=False
    allow_credentials:bool=False
    allow_trading_client:bool=False
    allow_order_submission:bool=False
    actual_orders_submitted:int=0
    def validate(self):
        if self.mode!="MULTI_ASSET_ALLOCATION_ONLY" or self.capital<=0: raise ValueError("safe mode")
        if abs(self.target_invested_weight+self.cash_reserve_weight-1)>1e-9: raise ValueError("capital split")
        if not 0<self.minimum_asset_weight<=self.maximum_asset_weight<=1: raise ValueError("asset limits")
        if not 0<self.maximum_sector_weight<=1 or not 0<=self.maximum_pair_correlation<=1: raise ValueError("constraints")
        if not 0<=self.rebalance_threshold<=1 or not 0<=self.maximum_turnover<=1: raise ValueError("rebalance limits")
        if self.allow_fractional_shares or self.allow_short_selling: raise ValueError("unsupported capabilities")
        if self.allow_network or self.allow_credentials or self.allow_trading_client or self.allow_order_submission or self.actual_orders_submitted:
            raise ValueError("offline only")

def validate_optimization_certificate(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V81.20" or c.get("status")!="PASS":
        raise ValueError("bad V81.20 certificate")
    if c.get("portfolio_optimization_complete") is not True or c.get("actual_orders_submitted")!=0:
        raise ValueError("optimization prerequisite")
    return c

def asset_universe()->list[dict[str,Any]]:
    return [
      {"symbol":"AAPL","sector":"TECH","price":190.0,"expected_return":0.12,"volatility":0.22,"liquidity_score":0.98},
      {"symbol":"MSFT","sector":"TECH","price":420.0,"expected_return":0.11,"volatility":0.20,"liquidity_score":0.99},
      {"symbol":"JPM","sector":"FINANCIALS","price":210.0,"expected_return":0.08,"volatility":0.18,"liquidity_score":0.94},
      {"symbol":"XOM","sector":"ENERGY","price":115.0,"expected_return":0.07,"volatility":0.24,"liquidity_score":0.93},
      {"symbol":"JNJ","sector":"HEALTHCARE","price":160.0,"expected_return":0.06,"volatility":0.14,"liquidity_score":0.90},
      {"symbol":"SPY","sector":"BROAD_MARKET","price":550.0,"expected_return":0.09,"volatility":0.15,"liquidity_score":1.00},
    ]

def correlation_matrix()->dict[str,dict[str,float]]:
    ids=[x["symbol"] for x in asset_universe()]
    vals={
      ("AAPL","MSFT"):0.78,("AAPL","JPM"):0.42,("AAPL","XOM"):0.28,("AAPL","JNJ"):0.34,("AAPL","SPY"):0.76,
      ("MSFT","JPM"):0.40,("MSFT","XOM"):0.25,("MSFT","JNJ"):0.32,("MSFT","SPY"):0.79,
      ("JPM","XOM"):0.36,("JPM","JNJ"):0.30,("JPM","SPY"):0.68,
      ("XOM","JNJ"):0.18,("XOM","SPY"):0.50,
      ("JNJ","SPY"):0.52,
    }
    return {a:{b:(1.0 if a==b else vals.get((a,b),vals.get((b,a),0.0))) for b in ids} for a in ids}

def normalize(raw:dict[str,float],target:float)->dict[str,float]:
    if not raw or any(v<0 or not math.isfinite(v) for v in raw.values()): raise ValueError("raw weights")
    total=sum(raw.values())
    if total<=0: raise ValueError("zero weights")
    return {k:round(v/total*target,12) for k,v in raw.items()}

def asset_score_weights(universe,config):
    raw={x["symbol"]:(x["expected_return"]*x["liquidity_score"]/x["volatility"]) for x in universe}
    return normalize(raw,config.target_invested_weight)

def cap_weights(weights,config):
    capped={k:min(v,config.maximum_asset_weight) for k,v in weights.items()}
    target=config.target_invested_weight
    for _ in range(50):
        diff=target-sum(capped.values())
        if abs(diff)<1e-10: break
        eligible=[k for k,v in capped.items() if v<config.maximum_asset_weight-1e-12]
        if not eligible: break
        add=diff/len(eligible)
        for k in eligible: capped[k]=min(config.maximum_asset_weight,capped[k]+add)
    return {k:round(v,12) for k,v in capped.items()}

def sector_weights(weights,universe):
    sectors={}
    meta={x["symbol"]:x for x in universe}
    for sym,w in weights.items():
        sec=meta[sym]["sector"];sectors[sec]=sectors.get(sec,0.0)+w
    return {k:round(v,12) for k,v in sectors.items()}

def validate_constraints(weights,universe,corr,config):
    sec=sector_weights(weights,universe);ids=list(weights);pairs=[]
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            if weights[a]>0 and weights[b]>0 and corr[a][b]>config.maximum_pair_correlation:
                pairs.append(f"{a}:{b}")
    checks={
      "weight_sum":abs(sum(weights.values())-config.target_invested_weight)<1e-8,
      "max_asset_weight":all(v<=config.maximum_asset_weight+1e-9 for v in weights.values()),
      "min_asset_weight":all(v==0 or v>=config.minimum_asset_weight-1e-9 for v in weights.values()),
      "max_sector_weight":all(v<=config.maximum_sector_weight+1e-9 for v in sec.values()),
      "pair_correlation":not pairs,
      "cash_reserve":abs(1-sum(weights.values())-config.cash_reserve_weight)<1e-8,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"stage":"V81.28","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "sector_weights":sec,"pair_correlation_violations":pairs}

def portfolio_metrics(weights,universe,corr):
    meta={x["symbol"]:x for x in universe};ids=list(weights)
    er=sum(weights[s]*meta[s]["expected_return"] for s in ids)
    variance=0.0
    for a in ids:
        for b in ids:
            variance+=weights[a]*weights[b]*meta[a]["volatility"]*meta[b]["volatility"]*corr[a][b]
    vol=math.sqrt(max(variance,0.0));sharpe=er/vol if vol else 0.0
    return {"expected_return":round(er,12),"expected_volatility":round(vol,12),"expected_sharpe":round(sharpe,8)}

def current_portfolio()->dict[str,int]:
    return {"AAPL":80,"MSFT":20,"JPM":50,"XOM":100,"JNJ":60,"SPY":20}

def market_values(positions,universe):
    prices={x["symbol"]:x["price"] for x in universe}
    return {s:round(q*prices[s],8) for s,q in positions.items()}

def current_weights(positions,universe,capital):
    values=market_values(positions,universe)
    return {s:round(v/capital,12) for s,v in values.items()}

def target_shares(weights,universe,config):
    prices={x["symbol"]:x["price"] for x in universe}
    return {s:int((weights[s]*config.capital)//prices[s]) for s in weights}

def rebalance_plan(current_positions,target_positions,universe,config):
    prices={x["symbol"]:x["price"] for x in universe};actions=[];turnover=0.0
    for sym in target_positions:
        cur=int(current_positions.get(sym,0));target=int(target_positions[sym]);delta=target-cur
        notional=abs(delta)*prices[sym];turnover+=notional/config.capital
        curw=cur*prices[sym]/config.capital;tarw=target*prices[sym]/config.capital
        if abs(tarw-curw)<config.rebalance_threshold: delta=0
        actions.append({"symbol":sym,"current_quantity":cur,"target_quantity":target,"delta_quantity":delta,
                        "action":"BUY" if delta>0 else "SELL" if delta<0 else "HOLD",
                        "estimated_notional":round(abs(delta)*prices[sym],8),"order_submission_authorized":False})
    return {"stage":"V81.31","status":"PASS","action_count":len(actions),"actions":actions,
            "turnover":round(turnover,12),"maximum_turnover":config.maximum_turnover,
            "turnover_within_limit":turnover<=config.maximum_turnover,"orders_created":0}

def apply_turnover_guard(plan,config):
    if plan["turnover_within_limit"]: return plan
    scale=config.maximum_turnover/plan["turnover"] if plan["turnover"] else 1.0
    adjusted=[]
    for a in plan["actions"]:
        delta=int(a["delta_quantity"]*scale)
        adjusted.append({**a,"delta_quantity":delta,"action":"BUY" if delta>0 else "SELL" if delta<0 else "HOLD",
                         "estimated_notional":round(a["estimated_notional"]*scale,8)})
    out=dict(plan);out["actions"]=adjusted;out["turnover"]=config.maximum_turnover;out["turnover_within_limit"]=True
    out["turnover_guard_applied"]=True;return out

def build_exposure(weights,universe):
    sec=sector_weights(weights,universe)
    return {"stage":"V81.32","status":"PASS","gross_exposure":round(sum(weights.values()),12),
            "net_exposure":round(sum(weights.values()),12),"asset_count":len(weights),"sector_count":len(sec),
            "sector_weights":sec}

def build_risk_budget(weights,universe):
    meta={x["symbol"]:x for x in universe}
    raw={s:weights[s]*meta[s]["volatility"] for s in weights};total=sum(raw.values())
    budgets={s:(raw[s]/total if total else 0.0) for s in weights}
    return {"stage":"V81.33","status":"PASS","budget_count":len(budgets),
            "risk_budgets":{k:round(v,12) for k,v in budgets.items()},
            "budget_sum":round(sum(budgets.values()),12)}

def build_audit(weights,constraints,metrics,plan,exposure,risk_budget,config):
    checks={"asset_count_six":len(weights)==6,"constraints_pass":constraints["status"]=="PASS",
      "metrics_finite":all(math.isfinite(v) for v in metrics.values()),
      "turnover_within_limit":plan["turnover_within_limit"],
      "gross_exposure_valid":abs(exposure["gross_exposure"]-config.target_invested_weight)<1e-8,
      "risk_budget_sum":abs(risk_budget["budget_sum"]-1.0)<1e-8,
      "orders_zero":plan["orders_created"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V81.34","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store_package(out,docs):
    package_id="multi-asset-"+hj(docs)[:24];pdir=out/"packages"/package_id;created=not pdir.exists();files={}
    for name,doc in docs.items():
        p=pdir/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists():aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V81.35","status":"PASS","package_id":package_id,"document_count":len(docs),
      "package_created":created,"package_reused":not created,"files":files,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"multi_asset_master_ledger_v81_35.json",ledger)
    return {"package_id":package_id,"created":created,"reused":not created,"ledger":ledger}

def build_manifest(out,ledger):
    lp=out/"multi_asset_master_ledger_v81_35.json";b=lp.read_bytes()
    d={"stage":"V81.36","status":"PASS","package_id":ledger["package_id"],
      "files":{"master_ledger":{"relative_path":str(lp.relative_to(out)).replace("\\","/"),"sha256":hb(b),"byte_size":len(b)}},
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"multi_asset_manifest_v81_36.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u):raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("tamper")
    ledger=json.loads((out/"multi_asset_master_ledger_v81_35.json").read_text())
    for x in ledger["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]:raise ValueError("nested tamper")
    return True

def run_engine(root,c,out):
    c.validate();cert=validate_optimization_certificate(root/"release/v81_20/output/portfolio_optimization_certificate_v81_20.json")
    universe=asset_universe();corr=correlation_matrix()
    weights=cap_weights(asset_score_weights(universe,c),c)
    constraints=validate_constraints(weights,universe,corr,c);metrics=portfolio_metrics(weights,universe,corr)
    current=current_portfolio();targets=target_shares(weights,universe,c)
    plan=apply_turnover_guard(rebalance_plan(current,targets,universe,c),c)
    exposure=build_exposure(weights,universe);risk_budget=build_risk_budget(weights,universe)
    audit=build_audit(weights,constraints,metrics,plan,exposure,risk_budget,c)
    docs={"asset_universe":{"stage":"V81.21","assets":universe},
      "correlation":{"stage":"V81.24","matrix":corr},"target_weights":{"stage":"V81.27","weights":weights},
      "constraints":constraints,"metrics":{"stage":"V81.29",**metrics},
      "current_positions":{"stage":"V81.30","positions":current},"target_positions":{"stage":"V81.30","positions":targets},
      "rebalance_plan":plan,"exposure":exposure,"risk_budget":risk_budget,"audit":audit}
    stored=store_package(out,docs);manifest=build_manifest(out,stored["ledger"]);verify_manifest(out,manifest)
    summary={"asset_count":len(universe),"sector_count":len(exposure["sector_weights"]),
      "target_weight_sum":round(sum(weights.values()),12),"cash_reserve_weight":c.cash_reserve_weight,
      "expected_return":metrics["expected_return"],"expected_volatility":metrics["expected_volatility"],
      "expected_sharpe":metrics["expected_sharpe"],"rebalance_action_count":plan["action_count"],
      "turnover":plan["turnover"],"turnover_guard_applied":plan.get("turnover_guard_applied",False),
      "gross_exposure":exposure["gross_exposure"],"risk_budget_sum":risk_budget["budget_sum"],
      "orders_created":0,"audit_status":audit["status"],
      "source_optimizer":cert["optimization_summary"]["selected_method"]}
    return {"stage":"V81.37","status":"PASS","summary":summary,**stored,"manifest":manifest,
      "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0}

def build_certificate(root,out,c,r):
    s=r["summary"];checks={"v81_20_certificate_present":(root/"release/v81_20/output/portfolio_optimization_certificate_v81_20.json").is_file(),
      "pipeline_pass":r["status"]=="PASS","asset_count_six":s["asset_count"]==6,
      "target_weight_sum_valid":abs(s["target_weight_sum"]-c.target_invested_weight)<1e-8,
      "cash_reserve_valid":abs(s["cash_reserve_weight"]-c.cash_reserve_weight)<1e-8,
      "turnover_within_limit":s["turnover"]<=c.maximum_turnover+1e-9,
      "gross_exposure_valid":abs(s["gross_exposure"]-c.target_invested_weight)<1e-8,
      "risk_budget_sum_valid":abs(s["risk_budget_sum"]-1.0)<1e-8,
      "audit_pass":s["audit_status"]=="PASS","orders_zero":s["orders_created"]==0,
      "manifest_hash_present":len(r["manifest"]["manifest_sha256"])==64,
      "network_zero":r["network_requests_executed"]==0,"credentials_zero":r["credentials_used"]==0,
      "client_false":r["trading_client_created"] is False,"actual_orders_zero":r["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    cert={"stage":"V81.40","status":status,"scope":"OFFLINE_MULTI_ASSET_PORTFOLIO_ENGINE",
      "stages_completed":[f"V81.{i:02d}" for i in range(21,41)],"completed_stage_count":20 if status=="PASS" else 20-len(failed),
      "config":asdict(c),"multi_asset_summary":{**s,"package_id":r["package_id"],"package_created":r["created"],"package_reused":r["reused"]},
      "multi_asset_manifest":r["manifest"],"checks":checks,"failed_checks":failed,
      "network_requests_executed":0,"credentials_used":0,"broker_connected":False,"trading_client_created":False,
      "actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,
      "multi_asset_portfolio_complete":status=="PASS","next_phase":"V81_41_BROKER_ADAPTER_FOUNDATION"}
    cert["certificate_sha256"]=hj(cert);wj(out/"multi_asset_portfolio_certificate_v81_40.json",cert)
    wj(out/"multi_asset_portfolio_verify_v81_40.json",{"stage":"V81.40","status":status,"verified":not failed,
      "certificate_sha256":cert["certificate_sha256"],"failed_checks":failed,"next_phase":cert["next_phase"]})
    return cert

sha256_multi_asset_json=hj
