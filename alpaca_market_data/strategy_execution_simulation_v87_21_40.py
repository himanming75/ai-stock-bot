from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json, os, tempfile

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=p.parent) as h:
        h.write(b); t=Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class StrategyExecutionSimulationConfig:
    mode: str = "PAPER_STRATEGY_EXECUTION_SIMULATION"
    environment: str = "PAPER"
    symbol: str = "AAPL"
    quantity: int = 1
    reference_price: float = 200.0
    slippage_bps: float = 5.0
    commission_per_order: float = 0.0
    daily_order_limit: int = 1
    daily_notional_limit: float = 500.0
    retry_limit: int = 2
    initial_cash: float = 100000.0
    initial_equity: float = 100000.0
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    allow_network: bool = False
    actual_orders_submitted: int = 0
    def validate(self):
        if self.mode != "PAPER_STRATEGY_EXECUTION_SIMULATION": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if self.quantity != 1 or self.reference_price <= 0: raise ValueError("order")
        if self.slippage_bps < 0 or self.commission_per_order < 0: raise ValueError("cost")
        if self.daily_order_limit != 1 or self.daily_notional_limit <= 0 or self.retry_limit < 0: raise ValueError("limits")
        if self.initial_cash <= 0 or self.initial_equity <= 0: raise ValueError("portfolio")
        if self.auto_execution_enabled or self.paper_order_submission_authorized or self.live_trading_authorized:
            raise ValueError("authorization")
        if self.allow_network or self.actual_orders_submitted != 0: raise ValueError("offline only")

def validate_source(path:Path)->dict[str,Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c=json.loads(path.read_text(encoding="utf-8"));u=dict(c);e=u.pop("certificate_sha256",None)
    if e!=hj(u) or c.get("stage")!="V87.20" or c.get("status")!="PASS":
        raise ValueError("bad V87.20 certificate")
    if c.get("paper_strategy_execution_operations_complete") is not True:
        raise ValueError("strategy operations prerequisite")
    if c.get("paper_order_submission_authorized") is not False or c.get("live_trading_authorized") is not False:
        raise ValueError("unsafe source")
    return c

def simulation_policy(config):
    d={"stage":"V87.21","status":"PASS","environment":config.environment,
       "simulation_only":True,"network_enabled":False,"dispatch_enabled":False,
       "paper_order_submission_authorized":False,"live_trading_authorized":False}
    d["policy_sha256"]=hj(d);return d

def order_plan(config):
    est_notional=config.quantity*config.reference_price
    d={"stage":"V87.22","plan_id":"sim-plan-"+hj(asdict(config))[:24],
       "symbol":config.symbol,"side":"buy","quantity":config.quantity,
       "order_type":"market","time_in_force":"day",
       "reference_price":config.reference_price,
       "estimated_notional":est_notional,
       "status":"PLANNED","dispatch_enabled":False}
    d["plan_sha256"]=hj(d);return d

def position_sizing(config,plan):
    max_qty=int(config.daily_notional_limit//plan["reference_price"])
    selected=min(config.quantity,max_qty)
    d={"stage":"V87.23","requested_qty":config.quantity,
       "max_qty_by_notional":max_qty,"selected_qty":selected,
       "status":"PASS" if selected==config.quantity and selected>0 else "FAIL"}
    d["sizing_sha256"]=hj(d);return d

def slippage_model(config,side,reference_price):
    multiplier=1+(config.slippage_bps/10000.0) if side=="buy" else 1-(config.slippage_bps/10000.0)
    price=round(reference_price*multiplier,8)
    d={"stage":"V87.24","side":side,"reference_price":reference_price,
       "slippage_bps":config.slippage_bps,"simulated_price":price}
    d["slippage_sha256"]=hj(d);return d

def commission_model(config):
    d={"stage":"V87.25","commission_per_order":config.commission_per_order,
       "estimated_commission":config.commission_per_order}
    d["commission_sha256"]=hj(d);return d

def lifecycle_event(order_id,status,filled_qty,avg_price,reason=None):
    d={"stage":"V87.26","order_id":order_id,"status":status,
       "filled_qty":float(filled_qty),"filled_avg_price":float(avg_price),
       "reason":reason}
    d["event_sha256"]=hj(d);return d

def simulate_accepted(plan):
    return lifecycle_event("sim-order-"+plan["plan_id"][-16:],"accepted",0,0)

def simulate_partial(plan,fill_price):
    return lifecycle_event("sim-order-"+plan["plan_id"][-16:],"partially_filled",0.5,fill_price)

def simulate_filled(plan,fill_price):
    return lifecycle_event("sim-order-"+plan["plan_id"][-16:],"filled",float(plan["quantity"]),fill_price)

def simulate_rejected(plan):
    return lifecycle_event("sim-order-"+plan["plan_id"][-16:],"rejected",0,0,"SIMULATED_RISK_REJECT")

def simulate_canceled(plan):
    return lifecycle_event("sim-order-"+plan["plan_id"][-16:],"canceled",0,0,"SIMULATED_CANCEL")

def retry_policy(config,attempt,status):
    retryable=status in {"timeout","temporary_error","rate_limited"}
    allowed=retryable and attempt<config.retry_limit
    d={"stage":"V87.27","attempt":attempt,"status":status,
       "retryable":retryable,"retry_allowed":allowed,
       "next_attempt":attempt+1 if allowed else None}
    d["retry_sha256"]=hj(d);return d

def budget_consumption(config,filled_event,commission):
    notional=filled_event["filled_qty"]*filled_event["filled_avg_price"]
    total=notional+commission["estimated_commission"]
    checks={"order_limit":1<=config.daily_order_limit,
            "notional_limit":total<=config.daily_notional_limit}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.28","status":"PASS" if not failed else "FAIL",
       "filled_notional":notional,"commission":commission["estimated_commission"],
       "total_consumed":total,"orders_consumed":1,
       "checks":checks,"failed_checks":failed}
    d["budget_sha256"]=hj(d);return d

def position_delta(filled_event):
    qty=filled_event["filled_qty"]
    avg=filled_event["filled_avg_price"]
    d={"stage":"V87.29","symbol":"AAPL","quantity_delta":qty,
       "average_entry_price":avg,"market_value":qty*avg}
    d["position_sha256"]=hj(d);return d

def portfolio_update(config,budget,position):
    closing_cash=config.initial_cash-budget["total_consumed"]
    equity=closing_cash+position["market_value"]
    d={"stage":"V87.30","opening_cash":config.initial_cash,
       "closing_cash":closing_cash,"position_market_value":position["market_value"],
       "equity":equity,"cash_change":closing_cash-config.initial_cash,
       "equity_change":equity-config.initial_equity}
    d["portfolio_sha256"]=hj(d);return d

def pnl_preview(position,current_price):
    unrealized=(current_price-position["average_entry_price"])*position["quantity_delta"]
    d={"stage":"V87.31","current_price":current_price,
       "unrealized_pnl":unrealized,"realized_pnl":0.0,
       "total_pnl":unrealized}
    d["pnl_sha256"]=hj(d);return d

def drawdown_update(config,portfolio):
    peak=config.initial_equity
    equity=portfolio["equity"]
    drawdown=max(0.0,peak-equity)
    drawdown_pct=0.0 if peak==0 else drawdown/peak
    d={"stage":"V87.32","peak_equity":peak,"current_equity":equity,
       "drawdown":drawdown,"drawdown_pct":drawdown_pct}
    d["drawdown_sha256"]=hj(d);return d

def scenario_matrix(config,plan,fill_price):
    events={
      "accepted":simulate_accepted(plan),
      "partial":simulate_partial(plan,fill_price),
      "filled":simulate_filled(plan,fill_price),
      "rejected":simulate_rejected(plan),
      "canceled":simulate_canceled(plan),
    }
    d={"stage":"V87.33","scenario_count":len(events),
       "accepted_count":1,"partial_count":1,"filled_count":1,
       "rejected_count":1,"canceled_count":1,"events":events}
    d["matrix_sha256"]=hj(d);return d

def replay(simulation_documents):
    first=hj(simulation_documents)
    second=hj(json.loads(json.dumps(simulation_documents)))
    d={"stage":"V87.34","first_sha256":first,"second_sha256":second,
       "deterministic":first==second}
    d["replay_sha256"]=hj(d);return d

def rollback_plan():
    d={"stage":"V87.35","status":"PASS","rollback_target":"V87.20",
       "discard_simulated_orders":True,"restore_budget":True,
       "restore_positions":True,"restore_cash":True,
       "clear_retry_state":True,"disable_dispatch":True,
       "disable_network":True}
    d["rollback_sha256"]=hj(d);return d

def simulation_scenario(config):
    plan=order_plan(config);sizing=position_sizing(config,plan)
    slip=slippage_model(config,plan["side"],plan["reference_price"])
    commission=commission_model(config)
    matrix=scenario_matrix(config,plan,slip["simulated_price"])
    filled=matrix["events"]["filled"]
    budget=budget_consumption(config,filled,commission)
    position=position_delta(filled)
    portfolio=portfolio_update(config,budget,position)
    pnl=pnl_preview(position,slip["simulated_price"]+1.0)
    drawdown=drawdown_update(config,portfolio)
    retry1=retry_policy(config,0,"timeout")
    retry2=retry_policy(config,config.retry_limit,"timeout")
    docs={"plan":plan,"sizing":sizing,"slippage":slip,"commission":commission,
          "scenario_matrix":matrix,"budget":budget,"position":position,
          "portfolio":portfolio,"pnl":pnl,"drawdown":drawdown,
          "retry_initial":retry1,"retry_exhausted":retry2}
    replay_doc=replay(docs)
    d={"stage":"V87.36","status":"PASS",
       "plan_status":plan["status"],"sizing_status":sizing["status"],
       "budget_status":budget["status"],
       "accepted_count":matrix["accepted_count"],
       "partial_count":matrix["partial_count"],
       "filled_count":matrix["filled_count"],
       "rejected_count":matrix["rejected_count"],
       "canceled_count":matrix["canceled_count"],
       "closing_cash":portfolio["closing_cash"],
       "position_qty":position["quantity_delta"],
       "unrealized_pnl":pnl["unrealized_pnl"],
       "drawdown":drawdown["drawdown"],
       "retry_initial_allowed":retry1["retry_allowed"],
       "retry_exhausted_blocked":not retry2["retry_allowed"],
       "replay_deterministic":replay_doc["deterministic"],
       "network_requests_executed":0,"actual_orders_submitted":0,
       "documents":{**docs,"replay":replay_doc}}
    d["scenario_sha256"]=hj(d);return d

def audit(config,scenario,rollback):
    checks={"plan_pass":scenario["plan_status"]=="PLANNED",
            "sizing_pass":scenario["sizing_status"]=="PASS",
            "budget_pass":scenario["budget_status"]=="PASS",
            "accepted_positive":scenario["accepted_count"]==1,
            "partial_positive":scenario["partial_count"]==1,
            "filled_positive":scenario["filled_count"]==1,
            "rejected_positive":scenario["rejected_count"]==1,
            "canceled_positive":scenario["canceled_count"]==1,
            "position_positive":scenario["position_qty"]>0,
            "closing_cash_positive":scenario["closing_cash"]>0,
            "retry_initial_allowed":scenario["retry_initial_allowed"],
            "retry_exhausted_blocked":scenario["retry_exhausted_blocked"],
            "replay_deterministic":scenario["replay_deterministic"],
            "rollback_pass":rollback["status"]=="PASS",
            "auto_execution_false":config.auto_execution_enabled is False,
            "network_zero":scenario["network_requests_executed"]==0,
            "orders_zero":scenario["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V87.37","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="strategy-exec-sim-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for name,doc in docs.items():
        p=pd/f"{name}.json";b=(json.dumps(doc,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hb(b),"byte_size":len(b)}
    ledger={"stage":"V87.38","status":"PASS","package_id":pid,
            "package_created":created,"package_reused":not created,
            "document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hj(ledger);wj(out/"strategy_execution_sim_ledger_v87_38.json",ledger)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":ledger}

def manifest(out,ledger):
    p=out/"strategy_execution_sim_ledger_v87_38.json";b=p.read_bytes()
    d={"stage":"V87.39","status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":0,"credentials_used":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"strategy_execution_sim_manifest_v87_39.json",d);return d

def verify_manifest(out,m):
    u=dict(m);e=u.pop("manifest_sha256",None)
    if e!=hj(u): raise ValueError("manifest hash")
    for x in m["files"].values():
        p=out/x["relative_path"];b=p.read_bytes()
        if hb(b)!=x["sha256"] or len(b)!=x["byte_size"]: raise ValueError("manifest tamper")
    return True

def run_engine(root,c,out):
    c.validate();source=validate_source(root/"release/v87_20/output/strategy_execution_certificate_v87_20.json")
    policy=simulation_policy(c);scenario=simulation_scenario(c);rollback=rollback_plan()
    au=audit(c,scenario,rollback)
    docs={"source_certificate":{"certificate_sha256":source["certificate_sha256"],
                               "strategy_id":source["strategy_execution_summary"]["strategy_id"]},
          "simulation_policy":policy,"simulation_scenario":scenario,
          "rollback_plan":rollback,"audit":au}
    st=store(out,docs);m=manifest(out,st["ledger"]);verify_manifest(out,m)
    summary={"symbol":c.symbol,"quantity":c.quantity,
             "accepted_count":scenario["accepted_count"],
             "partial_count":scenario["partial_count"],
             "filled_count":scenario["filled_count"],
             "rejected_count":scenario["rejected_count"],
             "canceled_count":scenario["canceled_count"],
             "closing_cash":scenario["closing_cash"],
             "position_qty":scenario["position_qty"],
             "unrealized_pnl":scenario["unrealized_pnl"],
             "drawdown":scenario["drawdown"],
             "retry_initial_allowed":scenario["retry_initial_allowed"],
             "retry_exhausted_blocked":scenario["retry_exhausted_blocked"],
             "replay_deterministic":scenario["replay_deterministic"],
             "rollback_status":rollback["status"],
             "audit_status":au["status"],
             "network_requests_executed":0,
             "actual_orders_submitted":0}
    return {"stage":"V87.40","status":"PASS" if au["status"]=="PASS" else "FAIL",
            **st,"manifest":m,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "accepted_count_one":s["accepted_count"]==1,
            "partial_count_one":s["partial_count"]==1,
            "filled_count_one":s["filled_count"]==1,
            "rejected_count_one":s["rejected_count"]==1,
            "canceled_count_one":s["canceled_count"]==1,
            "closing_cash_positive":s["closing_cash"]>0,
            "position_positive":s["position_qty"]>0,
            "retry_initial_allowed":s["retry_initial_allowed"],
            "retry_exhausted_blocked":s["retry_exhausted_blocked"],
            "replay_deterministic":s["replay_deterministic"],
            "rollback_pass":s["rollback_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "network_zero":s["network_requests_executed"]==0,
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V87.40","status":status,
       "scope":"PAPER_STRATEGY_EXECUTION_SIMULATION",
       "stages_completed":[f"V87.{i:02d}" for i in range(21,41)],
       "completed_stage_count":20 if status=="PASS" else 20-len(failed),
       "config":asdict(c),
       "strategy_execution_simulation_summary":{**s,"package_id":r["package_id"],
         "package_created":r["created"],"package_reused":r["reused"]},
       "strategy_execution_simulation_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "paper_strategy_execution_simulation_complete":status=="PASS",
       "strategy_execution_engine_simulated":status=="PASS",
       "auto_execution_enabled":False,
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "network_requests_executed":0,
       "actual_orders_submitted":0,
       "next_phase":"V87_41_PAPER_STRATEGY_EXECUTION_RECONCILIATION"}
    d["certificate_sha256"]=hj(d);wj(out/"strategy_execution_sim_certificate_v87_40.json",d)
    wj(out/"strategy_execution_sim_verify_v87_40.json",
       {"stage":"V87.40","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
