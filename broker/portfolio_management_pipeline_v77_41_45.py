from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math

class PortfolioManagementError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def safety() -> dict:
    return {
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
    }

@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    artifact_sha256: str
    verification_sha256: str
    next_phase: str
    output_files: tuple[str, ...]
    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "status": self.status,
            "artifact_sha256": self.artifact_sha256,
            "verification_sha256": self.verification_sha256,
            "next_phase": self.next_phase,
            "output_files": list(self.output_files),
        }

def build_paper_portfolio_state(
    risk_certificate_path: Path,
    risk_gate_path: Path,
    strategy_input_path: Path,
    output_dir: Path,
    *,
    starting_cash: float = 100000.0,
) -> StageResult:
    cert = load_json(risk_certificate_path)
    gate = load_json(risk_gate_path)
    strategy = load_json(strategy_input_path)
    if cert.get("certificate_id") != "RISK-MANAGEMENT-AUDIT-V77.40" or cert.get("status") != "PASS":
        raise PortfolioManagementError("invalid V77.40 risk certificate")
    if gate.get("stage") != "V77.39" or gate.get("status") != "PASS":
        raise PortfolioManagementError("invalid V77.39 risk safety gate")
    if strategy.get("stage") != "V77.31" or strategy.get("status") != "PASS":
        raise PortfolioManagementError("invalid V77.31 strategy input")
    if starting_cash <= 0:
        raise PortfolioManagementError("starting_cash must be positive")

    feature = strategy["feature_set"]
    qty = int(gate.get("approved_quantity", 0))
    price = float(feature["close"])
    notional = round(qty * price, 2)
    reserved_cash = notional
    available_cash = round(starting_cash - reserved_cash, 2)
    if available_cash < -0.01:
        raise PortfolioManagementError("approved position exceeds starting cash")
    positions = []
    if qty > 0:
        positions.append({
            "symbol": feature["symbol"],
            "quantity": qty,
            "average_cost": round(price, 8),
            "market_price": round(price, 8),
            "market_value": notional,
        })
    state = {
        "schema_version": "v77.41.paper_portfolio_state_engine.1",
        "stage": "V77.41",
        "status": "PASS",
        "portfolio_id": "PAPER-PORTFOLIO-V77-41",
        "starting_cash": round(starting_cash,2),
        "cash_balance": available_cash,
        "reserved_cash": reserved_cash,
        "open_position_count": len(positions),
        "positions": positions,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "portfolio_equity": round(available_cash + reserved_cash,2),
        "buying_power": max(0.0, available_cash),
        "source_risk_certificate_sha256": cert.get("certificate_sha256"),
        "source_risk_gate_sha256": gate.get("risk_safety_gate_sha256"),
        "orders_created": 0,
        "safety": safety(),
        "next_phase": "V77_42_PORTFOLIO_POSITION_LEDGER",
    }
    state["portfolio_state_sha256"] = digest_json({k:v for k,v in state.items() if k != "portfolio_state_sha256"})
    verification = {
        "schema_version":"v77.41.paper_portfolio_state_engine_verification.1",
        "stage":"V77.41","status":"PASS","verified":True,"error_count":0,"errors":[],
        "portfolio_state_sha256":state["portfolio_state_sha256"],"next_phase":state["next_phase"],
    }
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    sf=output_dir/"paper_portfolio_state_v77_41.json";vf=output_dir/"paper_portfolio_state_verification_v77_41.json"
    write_json(sf,state);write_json(vf,verification)
    return StageResult("V77.41","PASS",state["portfolio_state_sha256"],verification["verification_sha256"],state["next_phase"],(str(sf),str(vf)))

def build_position_ledger(portfolio_state_path: Path, output_dir: Path) -> StageResult:
    state=load_json(portfolio_state_path)
    if state.get("stage")!="V77.41" or state.get("status")!="PASS":
        raise PortfolioManagementError("invalid V77.41 portfolio state")
    previous="0"*64;entries=[];errors=[]
    seen=set()
    for idx,pos in enumerate(state.get("positions",[]),start=1):
        symbol=pos.get("symbol")
        checks=[]
        if symbol in seen:checks.append("duplicate_symbol")
        seen.add(symbol)
        if int(pos.get("quantity",0))<0:checks.append("negative_quantity")
        if float(pos.get("average_cost",0))<=0:checks.append("invalid_average_cost")
        if float(pos.get("market_price",0))<=0:checks.append("invalid_market_price")
        market_value=round(float(pos.get("quantity",0))*float(pos.get("market_price",0)),2)
        unrealized=round((float(pos.get("market_price",0))-float(pos.get("average_cost",0)))*float(pos.get("quantity",0)),2)
        entry={
            "sequence":idx,"symbol":symbol,"quantity":int(pos.get("quantity",0)),
            "average_cost":float(pos.get("average_cost",0)),"market_price":float(pos.get("market_price",0)),
            "market_value":market_value,"unrealized_pnl":unrealized,
            "validation_status":"PASS" if not checks else "FAIL","errors":checks,
            "previous_entry_sha256":previous,
        }
        entry["entry_sha256"]=digest_json({k:v for k,v in entry.items() if k!="entry_sha256"})
        previous=entry["entry_sha256"];entries.append(entry)
        errors.extend([f"{symbol}:{x}" for x in checks])
    total_value=sum(x["market_value"] for x in entries)
    for entry in entries:
        entry["position_weight"]=0.0 if total_value==0 else round(entry["market_value"]/total_value,8)
    status="PASS" if not errors else "FAIL"
    ledger={
        "schema_version":"v77.42.portfolio_position_ledger.1","stage":"V77.42","status":status,
        "source_portfolio_state_sha256":state.get("portfolio_state_sha256"),
        "entry_count":len(entries),"entries":entries,"ledger_head_sha256":previous,
        "gross_market_value":round(total_value,2),"error_count":len(errors),"errors":errors,
        "safety":safety(),"next_phase":"V77_43_PORTFOLIO_VALUATION_ENGINE",
    }
    ledger["position_ledger_sha256"]=digest_json({k:v for k,v in ledger.items() if k!="position_ledger_sha256"})
    verification={"schema_version":"v77.42.portfolio_position_ledger_verification.1","stage":"V77.42",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "position_ledger_sha256":ledger["position_ledger_sha256"],"next_phase":ledger["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    lf=output_dir/"portfolio_position_ledger_v77_42.json";vf=output_dir/"portfolio_position_ledger_verification_v77_42.json"
    write_json(lf,ledger);write_json(vf,verification)
    return StageResult("V77.42",status,ledger["position_ledger_sha256"],verification["verification_sha256"],ledger["next_phase"],(str(lf),str(vf)))

def value_portfolio(portfolio_state_path: Path, position_ledger_path: Path, output_dir: Path) -> StageResult:
    state=load_json(portfolio_state_path);ledger=load_json(position_ledger_path)
    if state.get("stage")!="V77.41" or ledger.get("stage")!="V77.42" or ledger.get("status")!="PASS":
        raise PortfolioManagementError("invalid state or ledger")
    cash=float(state.get("cash_balance",0))
    market_value=sum(float(x.get("market_value",0)) for x in ledger.get("entries",[]))
    unrealized=sum(float(x.get("unrealized_pnl",0)) for x in ledger.get("entries",[]))
    equity=round(cash+market_value,2)
    starting=float(state.get("starting_cash",0))
    total_return=0.0 if starting==0 else round((equity-starting)/starting,10)
    gross_exposure=0.0 if equity<=0 else round(market_value/equity,10)
    valuation={
        "schema_version":"v77.43.portfolio_valuation_engine.1","stage":"V77.43","status":"PASS",
        "valuation_id":"PORTFOLIO-VALUATION-V77-43","cash":round(cash,2),
        "market_value":round(market_value,2),"portfolio_equity":equity,
        "gross_exposure":gross_exposure,"net_exposure":gross_exposure,
        "realized_pnl":round(float(state.get("realized_pnl",0)),2),
        "unrealized_pnl":round(unrealized,2),"total_pnl":round(equity-starting,2),
        "portfolio_return":total_return,"drawdown":min(0.0,total_return),
        "source_portfolio_state_sha256":state.get("portfolio_state_sha256"),
        "source_position_ledger_sha256":ledger.get("position_ledger_sha256"),
        "orders_created":0,"safety":safety(),"next_phase":"V77_44_PORTFOLIO_SAFETY_GATE",
    }
    valuation["portfolio_valuation_sha256"]=digest_json({k:v for k,v in valuation.items() if k!="portfolio_valuation_sha256"})
    verification={"schema_version":"v77.43.portfolio_valuation_engine_verification.1","stage":"V77.43",
        "status":"PASS","verified":True,"error_count":0,"errors":[],
        "portfolio_valuation_sha256":valuation["portfolio_valuation_sha256"],"next_phase":valuation["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    df=output_dir/"portfolio_valuation_v77_43.json";vf=output_dir/"portfolio_valuation_verification_v77_43.json"
    write_json(df,valuation);write_json(vf,verification)
    return StageResult("V77.43","PASS",valuation["portfolio_valuation_sha256"],verification["verification_sha256"],valuation["next_phase"],(str(df),str(vf)))

def run_portfolio_safety_gate(
    portfolio_state_path: Path,
    position_ledger_path: Path,
    valuation_path: Path,
    output_dir: Path,
    *,
    max_gross_exposure: float = 0.80,
) -> StageResult:
    state=load_json(portfolio_state_path);ledger=load_json(position_ledger_path);valuation=load_json(valuation_path)
    errors=[]
    if state.get("stage")!="V77.41" or ledger.get("stage")!="V77.42" or valuation.get("stage")!="V77.43":errors.append("stage_chain")
    if float(state.get("cash_balance",0)) < -0.01:errors.append("negative_cash")
    symbols=[x.get("symbol") for x in ledger.get("entries",[])]
    if len(symbols)!=len(set(symbols)):errors.append("duplicate_position")
    if any(int(x.get("quantity",0))<0 for x in ledger.get("entries",[])):errors.append("negative_quantity")
    if float(valuation.get("gross_exposure",0))>max_gross_exposure+1e-9:errors.append("gross_exposure_limit")
    if any(x.get("orders_created")!=0 for x in (state,valuation)):errors.append("order_creation_detected")
    for doc,key in ((state,"portfolio_state_sha256"),(ledger,"position_ledger_sha256"),(valuation,"portfolio_valuation_sha256")):
        if doc.get(key)!=digest_json({k:v for k,v in doc.items() if k!=key}):errors.append(key)
    status="PASS" if not errors else "FAIL"
    gate={
        "schema_version":"v77.44.portfolio_safety_gate.1","stage":"V77.44","status":status,
        "decision":"ALLOW_PAPER_PORTFOLIO" if not errors else "BLOCK_PORTFOLIO",
        "error_count":len(errors),"errors":errors,"max_gross_exposure":max_gross_exposure,
        "portfolio_equity":valuation.get("portfolio_equity"),"gross_exposure":valuation.get("gross_exposure"),
        "source_portfolio_state_sha256":state.get("portfolio_state_sha256"),
        "source_position_ledger_sha256":ledger.get("position_ledger_sha256"),
        "source_portfolio_valuation_sha256":valuation.get("portfolio_valuation_sha256"),
        "orders_created":0,"safety":safety(),"next_phase":"V77_45_PORTFOLIO_AUDIT_CERTIFICATE",
    }
    gate["portfolio_safety_gate_sha256"]=digest_json({k:v for k,v in gate.items() if k!="portfolio_safety_gate_sha256"})
    verification={"schema_version":"v77.44.portfolio_safety_gate_verification.1","stage":"V77.44",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "portfolio_safety_gate_sha256":gate["portfolio_safety_gate_sha256"],"next_phase":gate["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    gf=output_dir/"portfolio_safety_gate_v77_44.json";vf=output_dir/"portfolio_safety_gate_verification_v77_44.json"
    write_json(gf,gate);write_json(vf,verification)
    return StageResult("V77.44",status,gate["portfolio_safety_gate_sha256"],verification["verification_sha256"],gate["next_phase"],(str(gf),str(vf)))

def issue_portfolio_certificate(v41: Path,v42: Path,v43: Path,v44: Path,output_dir: Path)->StageResult:
    docs=[load_json(p) for p in (v41,v42,v43,v44)];expected=["V77.41","V77.42","V77.43","V77.44"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v77.45.portfolio_audit_certificate.1","stage":"V77.45",
        "certificate_id":"PORTFOLIO-AUDIT-V77.45","status":status,
        "decision":"portfolio_certified" if not errors else "portfolio_rejected",
        "certified_stages":expected,"stage_count":4,
        "anchors":{"v77_41_verification_sha256":docs[0].get("verification_sha256"),
                   "v77_42_verification_sha256":docs[1].get("verification_sha256"),
                   "v77_43_verification_sha256":docs[2].get("verification_sha256"),
                   "v77_44_verification_sha256":docs[3].get("verification_sha256")},
        "error_count":len(errors),"errors":errors,"safety":safety(),
        "next_phase":"V77_46_BACKTEST_INPUT_ADAPTER" if not errors else "REPAIR_V77_45",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    verification={"schema_version":"v77.45.portfolio_audit_certificate_verification.1","stage":"V77.45",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    cf=output_dir/"portfolio_audit_certificate_v77_45.json";vf=output_dir/"portfolio_audit_certificate_verification_v77_45.json"
    write_json(cf,cert);write_json(vf,verification)
    return StageResult("V77.45",status,cert["certificate_sha256"],verification["verification_sha256"],cert["next_phase"],(str(cf),str(vf)))
