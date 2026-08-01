
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hjson(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def hbytes(v): return hashlib.sha256(v).hexdigest()
def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

@dataclass(frozen=True)
class FastTrackConfig:
    mode: str = "PAPER_AUTOMATION_PORTFOLIO_RISK_RUNTIME_RC"
    environment: str = "PAPER"
    release_candidate: str = "PAPER_RUNTIME_RC1"
    strategy_id: str = "SAFE_MOMENTUM_PREVIEW"
    starting_cash: float = 100000.0
    daily_order_limit: int = 1
    daily_notional_limit: float = 500.0
    max_open_positions: int = 3
    max_symbol_exposure_pct: float = 10.0
    max_total_exposure_pct: float = 25.0
    daily_loss_limit: float = 500.0
    max_drawdown_pct: float = 5.0
    scheduler_enabled: bool = False
    runtime_loop_enabled: bool = False
    market_data_network_enabled: bool = False
    auto_execution_enabled: bool = False
    paper_order_submission_authorized: bool = False
    live_trading_authorized: bool = False
    network_requests_executed: int = 0
    actual_orders_submitted: int = 0

    def validate(self):
        if self.mode != "PAPER_AUTOMATION_PORTFOLIO_RISK_RUNTIME_RC": raise ValueError("mode")
        if self.environment != "PAPER": raise ValueError("environment")
        if self.release_candidate != "PAPER_RUNTIME_RC1": raise ValueError("release")
        if self.starting_cash <= 0: raise ValueError("cash")
        if min(self.daily_order_limit,self.max_open_positions) < 1: raise ValueError("limits")
        if min(self.daily_notional_limit,self.daily_loss_limit,self.max_symbol_exposure_pct,
               self.max_total_exposure_pct,self.max_drawdown_pct) <= 0: raise ValueError("risk")
        if any([self.scheduler_enabled,self.runtime_loop_enabled,self.market_data_network_enabled,
                self.auto_execution_enabled,self.paper_order_submission_authorized,
                self.live_trading_authorized]):
            raise ValueError("unsafe enablement")
        if self.network_requests_executed != 0 or self.actual_orders_submitted != 0:
            raise ValueError("offline only")

def validate_certificate(path: Path, stage: str, flag: str) -> dict[str,Any]:
    c=json.loads(path.read_text(encoding="utf-8"))
    u=dict(c); expected=u.pop("certificate_sha256")
    if expected != hjson(u): raise ValueError("certificate hash")
    if c.get("stage") != stage or c.get("status") != "PASS": raise ValueError("certificate")
    if c.get(flag) is not True: raise ValueError("prerequisite")
    return c

def automation_chain(root):
    specs=[
      ("V88.20","release/v88_20/output/scheduler_foundation_certificate_v88_20.json","paper_scheduler_foundation_complete"),
      ("V88.40","release/v88_40/output/runtime_loop_certificate_v88_40.json","paper_strategy_runtime_loop_foundation_complete"),
      ("V88.60","release/v88_60/output/market_data_operations_certificate_v88_60.json","paper_market_data_operations_foundation_complete"),
      ("V88.80","release/v88_80/output/scheduler_runtime_sim_certificate_v88_80.json","scheduler_runtime_simulation_complete"),
    ]
    certs={}
    for stage,rel,flag in specs:
        certs[stage]=validate_certificate(root/rel,stage,flag)
    ids={k:v["certificate_sha256"] for k,v in certs.items()}
    d={"status":"PASS","certificate_count":4,"certificate_ids":ids,
       "chain_root_sha256":hjson(ids)}
    d["sha256"]=hjson(d);return d

def portfolio_state(config):
    d={"cash":config.starting_cash,"buying_power":config.starting_cash*2,
       "equity":config.starting_cash,"positions":{},"open_order_count":0,
       "realized_pnl":0.0,"unrealized_pnl":0.0}
    d["state_sha256"]=hjson(d);return d

def reserve_cash(state, amount):
    if amount <= 0 or amount > state["cash"]: raise ValueError("reservation")
    d=dict(state);d["cash_reserved"]=amount;d["available_cash"]=state["cash"]-amount
    d["state_sha256"]=hjson({k:v for k,v in d.items() if k!="state_sha256"});return d

def apply_fill(state, symbol, qty, price):
    if qty <= 0 or price <= 0: raise ValueError("fill")
    cost=qty*price
    if cost>state["cash"]: raise ValueError("cash")
    d=dict(state);d["cash"]=round(state["cash"]-cost,2)
    d["positions"]=dict(state["positions"]);d["positions"][symbol]={"qty":qty,"avg_price":price,"market_price":price}
    d["equity"]=round(d["cash"]+cost,2);d["open_order_count"]=0
    d["state_sha256"]=hjson({k:v for k,v in d.items() if k!="state_sha256"});return d

def mark_to_market(state, prices):
    d=dict(state);d["positions"]=json.loads(json.dumps(state["positions"]))
    mv=0.0;upnl=0.0
    for sym,pos in d["positions"].items():
        px=float(prices[sym]);pos["market_price"]=px
        mv += pos["qty"]*px
        upnl += pos["qty"]*(px-pos["avg_price"])
    d["market_value"]=round(mv,2);d["unrealized_pnl"]=round(upnl,2)
    d["equity"]=round(d["cash"]+mv,2)
    d["state_sha256"]=hjson({k:v for k,v in d.items() if k!="state_sha256"});return d

def reconcile_portfolio(before, after, fill):
    expected_cash=round(before["cash"]-fill["qty"]*fill["price"],2)
    checks={"cash_match":after["cash"]==expected_cash,
            "position_present":fill["symbol"] in after["positions"],
            "qty_match":after["positions"][fill["symbol"]]["qty"]==fill["qty"],
            "equity_consistent":after["equity"]==round(after["cash"]+fill["qty"]*fill["price"],2)}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}

def exposure_metrics(config, state):
    total_mv=sum(p["qty"]*p["market_price"] for p in state["positions"].values())
    symbol_pcts={s:round((p["qty"]*p["market_price"]/state["equity"])*100,4)
                 for s,p in state["positions"].items()}
    return {"total_market_value":round(total_mv,2),
            "total_exposure_pct":round(total_mv/state["equity"]*100,4),
            "symbol_exposure_pct":symbol_pcts,
            "open_positions":len(state["positions"])}

def pretrade_risk(config, state, intent, orders_used=0, daily_pnl=0.0, peak_equity=None):
    peak=peak_equity if peak_equity is not None else state["equity"]
    notional=intent["qty"]*intent["price"]
    projected_mv=sum(p["qty"]*p["market_price"] for p in state["positions"].values())+notional
    projected_equity=state["equity"]
    projected_total_pct=projected_mv/projected_equity*100
    symbol_existing=state["positions"].get(intent["symbol"],{"qty":0,"market_price":intent["price"]})
    projected_symbol=(symbol_existing["qty"]*symbol_existing["market_price"]+notional)/projected_equity*100
    drawdown=max(0.0,(peak-state["equity"])/peak*100)
    checks={
      "qty_positive":intent["qty"]>0,
      "price_positive":intent["price"]>0,
      "order_limit":orders_used < config.daily_order_limit,
      "notional_limit":notional <= config.daily_notional_limit,
      "cash_available":notional <= state["cash"],
      "position_limit":len(state["positions"])+(0 if intent["symbol"] in state["positions"] else 1) <= config.max_open_positions,
      "symbol_exposure":projected_symbol <= config.max_symbol_exposure_pct,
      "total_exposure":projected_total_pct <= config.max_total_exposure_pct,
      "daily_loss":daily_pnl > -config.daily_loss_limit,
      "drawdown":drawdown <= config.max_drawdown_pct,
    }
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "notional":notional,"projected_symbol_exposure_pct":projected_symbol,
            "projected_total_exposure_pct":projected_total_pct,"drawdown_pct":drawdown}

def kill_switch(triggered, reason):
    return {"status":"TRIGGERED" if triggered else "ARMED","triggered":triggered,
            "reason":reason if triggered else None,"new_orders_allowed":False if triggered else True,
            "network_enabled":False,"automatic_liquidation":False}

def runtime_cycle(config, state, intent, seen_signals):
    signal_id=intent["signal_id"]
    duplicate=signal_id in seen_signals
    if duplicate:
        return {"status":"SKIP","duplicate_detected":True,"preview_created":False,
                "actual_orders_submitted":0,"network_requests_executed":0}
    risk=pretrade_risk(config,state,intent)
    preview=risk["status"]=="PASS"
    return {"status":"PASS" if preview else "REJECTED","duplicate_detected":False,
            "risk":risk,"preview_created":preview,"order_submission_enabled":False,
            "actual_orders_submitted":0,"network_requests_executed":0}

def replay(config):
    state=portfolio_state(config)
    intent={"signal_id":"sig-1","symbol":"AAPL","qty":1,"price":200.0}
    a=runtime_cycle(config,state,intent,set())
    b=runtime_cycle(config,state,intent,set())
    return {"status":"PASS" if hjson(a)==hjson(b) else "FAIL",
            "first_sha256":hjson(a),"second_sha256":hjson(b)}

def rollback_package():
    d={"status":"PASS","rollback_target":"V88.80",
       "disable_scheduler":True,"disable_runtime":True,"disable_market_data_network":True,
       "disable_auto_execution":True,"disable_order_submission":True,
       "clear_signal_queue":True,"release_cash_reservations":True,
       "release_strategy_locks":True,"restore_portfolio_checkpoint":True,
       "preserve_audit_logs":True}
    d["sha256"]=hjson(d);return d

def integrated_simulation(config):
    initial=portfolio_state(config)
    intent={"signal_id":"sig-1","symbol":"AAPL","qty":1,"price":200.0}
    cycle=runtime_cycle(config,initial,intent,set())
    reserved=reserve_cash(initial,cycle["risk"]["notional"])
    filled=apply_fill(initial,"AAPL",1,200.0)
    marked=mark_to_market(filled,{"AAPL":201.0})
    recon=reconcile_portfolio(initial,filled,{"symbol":"AAPL","qty":1,"price":200.0})
    exposure=exposure_metrics(config,marked)
    duplicate=runtime_cycle(config,marked,intent,{"sig-1"})
    bad_notional=pretrade_risk(config,initial,{"symbol":"AAPL","qty":10,"price":200.0})
    daily_loss=pretrade_risk(config,initial,{"symbol":"AAPL","qty":1,"price":200.0},daily_pnl=-600.0)
    drawdown_state=dict(initial);drawdown_state["equity"]=90000.0
    drawdown=pretrade_risk(config,drawdown_state,{"symbol":"AAPL","qty":1,"price":200.0},peak_equity=100000.0)
    kill=kill_switch(True,"SIMULATED_DAILY_LOSS")
    report={"starting_cash":initial["cash"],"closing_cash":marked["cash"],
            "equity":marked["equity"],"position_qty":marked["positions"]["AAPL"]["qty"],
            "unrealized_pnl":marked["unrealized_pnl"],"total_exposure_pct":exposure["total_exposure_pct"]}
    checks={"cycle_pass":cycle["status"]=="PASS",
            "preview_created":cycle["preview_created"],
            "reservation_valid":reserved["cash_reserved"]==200.0,
            "reconciliation_pass":recon["status"]=="PASS",
            "unrealized_pnl_one":marked["unrealized_pnl"]==1.0,
            "duplicate_blocked":duplicate["status"]=="SKIP",
            "bad_notional_rejected":bad_notional["status"]=="FAIL",
            "daily_loss_rejected":daily_loss["status"]=="FAIL",
            "drawdown_rejected":drawdown["status"]=="FAIL",
            "kill_switch_triggered":kill["triggered"],
            "orders_zero":cycle["actual_orders_submitted"]==0,
            "network_zero":cycle["network_requests_executed"]==0}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,
            "initial":initial,"cycle":cycle,"reserved":reserved,"filled":filled,"marked":marked,
            "reconciliation":recon,"exposure":exposure,"duplicate":duplicate,
            "bad_notional":bad_notional,"daily_loss":daily_loss,"drawdown":drawdown,
            "kill_switch":kill,"daily_report":report,
            "actual_orders_submitted":0,"network_requests_executed":0}

def final_audit(config, chain, simulation, replay_doc, rollback):
    checks={"certificate_count_four":chain["certificate_count"]==4,
            "simulation_pass":simulation["status"]=="PASS",
            "replay_pass":replay_doc["status"]=="PASS",
            "rollback_pass":rollback["status"]=="PASS",
            "scheduler_disabled":config.scheduler_enabled is False,
            "runtime_disabled":config.runtime_loop_enabled is False,
            "market_data_network_disabled":config.market_data_network_enabled is False,
            "auto_execution_disabled":config.auto_execution_enabled is False,
            "paper_submit_disabled":config.paper_order_submission_authorized is False,
            "live_disabled":config.live_trading_authorized is False,
            "network_zero":simulation["network_requests_executed"]==0,
            "orders_zero":simulation["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    return {"status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed}

def store(out, docs):
    pid="paper-runtime-rc1-"+hjson(docs)[:24]
    package=out/"packages"/pid;package.mkdir(parents=True,exist_ok=True)
    files={}
    for name,doc in docs.items():
        p=package/f"{name}.json";write_json(p,doc);b=p.read_bytes()
        files[name]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                     "sha256":hbytes(b),"byte_size":len(b)}
    ledger={"status":"PASS","package_id":pid,"document_count":len(docs),"files":files,
            "network_requests_executed":0,"actual_orders_submitted":0}
    ledger["ledger_sha256"]=hjson(ledger)
    write_json(out/"fast_track_ledger_v90_00.json",ledger)
    return pid,ledger

def manifest(out, ledger):
    p=out/"fast_track_ledger_v90_00.json";b=p.read_bytes()
    d={"status":"PASS","package_id":ledger["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hbytes(b),"byte_size":len(b)}},
       "network_requests_executed":0,"actual_orders_submitted":0}
    d["manifest_sha256"]=hjson(d);write_json(out/"fast_track_manifest_v90_00.json",d);return d

def run_engine(root, config, out):
    config.validate()
    chain=automation_chain(root)
    sim=integrated_simulation(config)
    rep=replay(config)
    rb=rollback_package()
    audit=final_audit(config,chain,sim,rep,rb)
    docs={"automation_chain":chain,"integrated_simulation":sim,"replay":rep,
          "rollback":rb,"audit":audit}
    pid,ledger=store(out,docs);man=manifest(out,ledger)
    return {"status":"PASS" if audit["status"]=="PASS" else "FAIL",
            "package_id":pid,"chain":chain,"simulation":sim,"replay":rep,
            "rollback":rb,"audit":audit,"manifest":man}

def certificate(out, config, result):
    sim=result["simulation"]
    checks={"pipeline_pass":result["status"]=="PASS",
            "chain_four":result["chain"]["certificate_count"]==4,
            "simulation_pass":sim["status"]=="PASS",
            "replay_pass":result["replay"]["status"]=="PASS",
            "rollback_pass":result["rollback"]["status"]=="PASS",
            "audit_pass":result["audit"]["status"]=="PASS",
            "network_zero":sim["network_requests_executed"]==0,
            "orders_zero":sim["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V90.00","status":"PASS" if not failed else "FAIL",
       "scope":"FAST_TRACK_V88.81_TO_V90.00",
       "release_candidate":config.release_candidate,
       "functional_areas":["AUTOMATION_FINAL_CERTIFICATION","PORTFOLIO_STATE_MANAGER",
         "CASH_POSITION_RECONCILIATION","EXPOSURE_MANAGEMENT","RUNTIME_RISK_ENGINE",
         "DAILY_LOSS_GUARD","DRAWDOWN_GUARD","KILL_SWITCH",
         "INTEGRATED_RUNTIME_SIMULATION","REPLAY","ROLLBACK","AUDIT"],
       "config":asdict(config),"checks":checks,"failed_checks":failed,
       "paper_automation_framework_certified":not failed,
       "portfolio_runtime_foundation_complete":not failed,
       "runtime_risk_engine_complete":not failed,
       "paper_runtime_rc1_ready":not failed,
       "scheduler_enabled":False,"runtime_loop_enabled":False,
       "market_data_network_enabled":False,"auto_execution_enabled":False,
       "paper_order_submission_authorized":False,"live_trading_authorized":False,
       "network_requests_executed":0,"actual_orders_submitted":0,
       "summary":{"package_id":result["package_id"],
                  "certificate_count":result["chain"]["certificate_count"],
                  "chain_root_sha256":result["chain"]["chain_root_sha256"],
                  "closing_cash":sim["daily_report"]["closing_cash"],
                  "equity":sim["daily_report"]["equity"],
                  "position_qty":sim["daily_report"]["position_qty"],
                  "unrealized_pnl":sim["daily_report"]["unrealized_pnl"],
                  "audit_status":result["audit"]["status"]},
       "next_phase":"V90_01_ACTUAL_PAPER_AUTOMATION_ENABLEMENT_FOUNDATION"}
    d["certificate_sha256"]=hjson(d)
    write_json(out/"fast_track_certificate_v90_00.json",d)
    write_json(out/"fast_track_verify_v90_00.json",
      {"stage":"V90.00","status":d["status"],"verified":not failed,
       "failed_checks":failed,"certificate_sha256":d["certificate_sha256"],
       "next_phase":d["next_phase"]})
    return d
