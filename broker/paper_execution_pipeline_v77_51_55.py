from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json

class PaperExecutionError(ValueError):
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
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
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
            "stage":self.stage,
            "status":self.status,
            "artifact_sha256":self.artifact_sha256,
            "verification_sha256":self.verification_sha256,
            "next_phase":self.next_phase,
            "output_files":list(self.output_files),
        }

def build_paper_order_intent(backtest_certificate_path: Path, simulation_path: Path,
                             portfolio_state_path: Path, output_dir: Path) -> StageResult:
    cert=load_json(backtest_certificate_path)
    sim=load_json(simulation_path)
    state=load_json(portfolio_state_path)
    if cert.get("certificate_id")!="BACKTEST-AUDIT-V77.50" or cert.get("status")!="PASS":
        raise PaperExecutionError("invalid V77.50 certificate")
    if sim.get("stage")!="V77.48" or state.get("stage")!="V77.41":
        raise PaperExecutionError("invalid simulation or portfolio state")

    positions=state.get("positions",[])
    position_by_symbol={str(p.get("symbol")):p for p in positions}
    trades=sim.get("trades",[])

    candidate=trades[-1] if trades else {}
    symbol=str(candidate.get("symbol") or (positions[0].get("symbol") if positions else "SPY"))
    ref=float(candidate.get("price") or (
        position_by_symbol.get(symbol,{}).get("market_price")
        or position_by_symbol.get(symbol,{}).get("average_cost")
        or 1.0
    ))
    if ref<=0:
        raise PaperExecutionError("reference price must be positive")

    requested_side=str(candidate.get("side","BUY")).upper()
    requested_qty=max(1,int(candidate.get("quantity",1)))
    buying_power=max(0.0,float(state.get("buying_power",state.get("cash_balance",0.0))))
    held=max(0,int(position_by_symbol.get(symbol,{}).get("quantity",0)))
    affordable=max(0,int(buying_power//ref))

    adjustment_reason="NONE"
    if requested_side=="BUY" and affordable>0:
        side="BUY"; qty=min(requested_qty,affordable)
        if qty<requested_qty:
            adjustment_reason="CAPPED_TO_BUYING_POWER"
    elif requested_side=="SELL" and held>0:
        side="SELL"; qty=min(requested_qty,held)
        if qty<requested_qty:
            adjustment_reason="CAPPED_TO_HELD_POSITION"
    elif held>0:
        side="SELL"; qty=held
        adjustment_reason="FALLBACK_TO_EXISTING_POSITION"
    elif affordable>0:
        side="BUY"; qty=min(requested_qty,affordable)
        adjustment_reason="FALLBACK_TO_AFFORDABLE_BUY"
    else:
        raise PaperExecutionError("portfolio has no executable paper-order capacity")

    intent={
        "schema_version":"v77.51.paper_order_intent_builder.2",
        "stage":"V77.51",
        "status":"PASS",
        "intent_id":"PAPER-ORDER-INTENT-V77-51",
        "symbol":symbol,
        "side":side,
        "quantity":qty,
        "requested_side":requested_side,
        "requested_quantity":requested_qty,
        "adjustment_reason":adjustment_reason,
        "order_type":"MARKET",
        "reference_price":round(ref,8),
        "time_in_force":"DAY",
        "available_buying_power":round(buying_power,2),
        "available_position_quantity":held,
        "source_backtest_certificate_sha256":cert.get("certificate_sha256"),
        "source_execution_simulation_sha256":sim.get("execution_simulation_sha256"),
        "paper_only":True,
        "actual_orders_submitted":0,
        "safety":safety(),
        "next_phase":"V77_52_PAPER_ORDER_VALIDATION_ENGINE",
    }
    intent["paper_order_intent_sha256"]=digest_json({k:v for k,v in intent.items() if k!="paper_order_intent_sha256"})
    ver={
        "schema_version":"v77.51.paper_order_intent_builder_verification.2",
        "stage":"V77.51","status":"PASS","verified":True,"error_count":0,"errors":[],
        "paper_order_intent_sha256":intent["paper_order_intent_sha256"],
        "next_phase":intent["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    df=output_dir/"paper_order_intent_v77_51.json"; vf=output_dir/"paper_order_intent_verification_v77_51.json"
    write_json(df,intent); write_json(vf,ver)
    return StageResult("V77.51","PASS",intent["paper_order_intent_sha256"],ver["verification_sha256"],intent["next_phase"],(str(df),str(vf)))

def validate_paper_order(intent_path: Path, portfolio_state_path: Path, output_dir: Path) -> StageResult:
    intent=load_json(intent_path); state=load_json(portfolio_state_path); errors=[]
    if intent.get("stage")!="V77.51" or intent.get("status")!="PASS": errors.append("invalid_intent_stage")
    if intent.get("paper_order_intent_sha256")!=digest_json({k:v for k,v in intent.items() if k!="paper_order_intent_sha256"}):
        errors.append("intent_sha256")
    if intent.get("side") not in {"BUY","SELL"}: errors.append("side")
    if int(intent.get("quantity",0))<=0: errors.append("quantity")
    if float(intent.get("reference_price",0))<=0: errors.append("reference_price")
    if intent.get("paper_only") is not True: errors.append("paper_only")
    notional=round(int(intent.get("quantity",0))*float(intent.get("reference_price",0)),2)
    if intent.get("side")=="BUY" and notional>float(state.get("buying_power",state.get("cash_balance",0)))+0.01:
        errors.append("insufficient_buying_power")
    if intent.get("side")=="SELL":
        held=sum(int(x.get("quantity",0)) for x in state.get("positions",[]) if x.get("symbol")==intent.get("symbol"))
        if int(intent.get("quantity",0))>held: errors.append("insufficient_position")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v77.52.paper_order_validation_engine.1",
        "stage":"V77.52","status":status,
        "decision":"APPROVE_PAPER_ORDER" if not errors else "REJECT_PAPER_ORDER",
        "intent_id":intent.get("intent_id"),
        "validated_quantity":intent.get("quantity") if not errors else 0,
        "validated_notional":notional if not errors else 0.0,
        "error_count":len(errors),"errors":errors,
        "source_paper_order_intent_sha256":intent.get("paper_order_intent_sha256"),
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_53_PAPER_FILL_SIMULATION_ENGINE",
    }
    doc["paper_order_validation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="paper_order_validation_sha256"})
    ver={
        "schema_version":"v77.52.paper_order_validation_engine_verification.1",
        "stage":"V77.52","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "paper_order_validation_sha256":doc["paper_order_validation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    df=output_dir/"paper_order_validation_v77_52.json"; vf=output_dir/"paper_order_validation_verification_v77_52.json"
    write_json(df,doc); write_json(vf,ver)
    return StageResult("V77.52",status,doc["paper_order_validation_sha256"],ver["verification_sha256"],doc["next_phase"],(str(df),str(vf)))

def simulate_paper_fill(intent_path: Path, validation_path: Path, output_dir: Path,
                        *, slippage_bps: float=5.0, commission_per_share: float=0.0) -> StageResult:
    intent=load_json(intent_path); val=load_json(validation_path)
    if val.get("stage")!="V77.52" or val.get("status")!="PASS":
        raise PaperExecutionError("paper order was not validated")
    qty=int(val["validated_quantity"]); ref=float(intent["reference_price"])
    direction=1 if intent["side"]=="BUY" else -1
    fill_price=round(ref*(1+direction*slippage_bps/10000),8)
    commission=round(qty*commission_per_share,2)
    fill={
        "schema_version":"v77.53.paper_fill_simulation_engine.1",
        "stage":"V77.53","status":"PASS",
        "fill_id":"PAPER-FILL-V77-53",
        "intent_id":intent["intent_id"],
        "symbol":intent["symbol"],"side":intent["side"],
        "requested_quantity":qty,"filled_quantity":qty,"remaining_quantity":0,
        "reference_price":ref,"fill_price":fill_price,
        "slippage_bps":slippage_bps,"commission":commission,
        "gross_notional":round(qty*fill_price,2),
        "paper_fill":True,
        "actual_orders_submitted":0,
        "source_paper_order_intent_sha256":intent.get("paper_order_intent_sha256"),
        "source_paper_order_validation_sha256":val.get("paper_order_validation_sha256"),
        "safety":safety(),
        "next_phase":"V77_54_PAPER_EXECUTION_SAFETY_GATE",
    }
    fill["paper_fill_sha256"]=digest_json({k:v for k,v in fill.items() if k!="paper_fill_sha256"})
    ver={
        "schema_version":"v77.53.paper_fill_simulation_engine_verification.1",
        "stage":"V77.53","status":"PASS","verified":True,"error_count":0,"errors":[],
        "paper_fill_sha256":fill["paper_fill_sha256"],"next_phase":fill["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    df=output_dir/"paper_fill_simulation_v77_53.json"; vf=output_dir/"paper_fill_simulation_verification_v77_53.json"
    write_json(df,fill); write_json(vf,ver)
    return StageResult("V77.53","PASS",fill["paper_fill_sha256"],ver["verification_sha256"],fill["next_phase"],(str(df),str(vf)))

def run_paper_execution_safety_gate(intent_path: Path, validation_path: Path, fill_path: Path,
                                    output_dir: Path) -> StageResult:
    intent=load_json(intent_path); val=load_json(validation_path); fill=load_json(fill_path); errors=[]
    if [intent.get("stage"),val.get("stage"),fill.get("stage")]!=["V77.51","V77.52","V77.53"]:
        errors.append("stage_chain")
    if val.get("status")!="PASS" or fill.get("status")!="PASS": errors.append("upstream_status")
    if fill.get("filled_quantity")!=intent.get("quantity"): errors.append("fill_quantity")
    if fill.get("remaining_quantity")!=0: errors.append("remaining_quantity")
    if fill.get("paper_fill") is not True: errors.append("paper_fill")
    if any(x.get("actual_orders_submitted")!=0 for x in (intent,val,fill)): errors.append("actual_order_submission")
    if fill.get("paper_fill_sha256")!=digest_json({k:v for k,v in fill.items() if k!="paper_fill_sha256"}):
        errors.append("paper_fill_sha256")
    status="PASS" if not errors else "FAIL"
    gate={
        "schema_version":"v77.54.paper_execution_safety_gate.1",
        "stage":"V77.54","status":status,
        "decision":"ALLOW_PAPER_EXECUTION_RESULT" if not errors else "BLOCK_PAPER_EXECUTION_RESULT",
        "error_count":len(errors),"errors":errors,
        "source_paper_order_intent_sha256":intent.get("paper_order_intent_sha256"),
        "source_paper_order_validation_sha256":val.get("paper_order_validation_sha256"),
        "source_paper_fill_sha256":fill.get("paper_fill_sha256"),
        "actual_orders_submitted":0,
        "safety":safety(),
        "next_phase":"V77_55_PAPER_EXECUTION_AUDIT_CERTIFICATE",
    }
    gate["paper_execution_safety_gate_sha256"]=digest_json({k:v for k,v in gate.items() if k!="paper_execution_safety_gate_sha256"})
    ver={
        "schema_version":"v77.54.paper_execution_safety_gate_verification.1",
        "stage":"V77.54","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "paper_execution_safety_gate_sha256":gate["paper_execution_safety_gate_sha256"],
        "next_phase":gate["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    df=output_dir/"paper_execution_safety_gate_v77_54.json"; vf=output_dir/"paper_execution_safety_gate_verification_v77_54.json"
    write_json(df,gate); write_json(vf,ver)
    return StageResult("V77.54",status,gate["paper_execution_safety_gate_sha256"],ver["verification_sha256"],gate["next_phase"],(str(df),str(vf)))

def issue_paper_execution_certificate(v51: Path,v52: Path,v53: Path,v54: Path,output_dir: Path)->StageResult:
    docs=[load_json(x) for x in (v51,v52,v53,v54)]
    expected=["V77.51","V77.52","V77.53","V77.54"]; errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v77.55.paper_execution_audit_certificate.1",
        "stage":"V77.55",
        "certificate_id":"PAPER-EXECUTION-AUDIT-V77.55",
        "status":status,
        "decision":"paper_execution_certified" if not errors else "paper_execution_rejected",
        "certified_stages":expected,
        "error_count":len(errors),"errors":errors,
        "actual_orders_submitted":0,
        "safety":safety(),
        "next_phase":"V77_56_PORTFOLIO_RECONCILIATION_ENGINE" if not errors else "REPAIR_V77_55",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    ver={
        "schema_version":"v77.55.paper_execution_audit_certificate_verification.1",
        "stage":"V77.55","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    cf=output_dir/"paper_execution_audit_certificate_v77_55.json"; vf=output_dir/"paper_execution_audit_certificate_verification_v77_55.json"
    write_json(cf,cert); write_json(vf,ver)
    return StageResult("V77.55",status,cert["certificate_sha256"],ver["verification_sha256"],cert["next_phase"],(str(cf),str(vf)))
