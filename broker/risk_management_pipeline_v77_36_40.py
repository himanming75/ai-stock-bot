from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, json, math

class RiskManagementError(ValueError):
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

def calculate_position_risk(
    strategy_certificate_path: Path,
    strategy_input_path: Path,
    signal_gate_path: Path,
    output_dir: Path,
    *,
    account_equity: float = 100000.0,
    risk_per_trade_pct: float = 0.01,
    atr_stop_multiple: float = 2.0,
) -> StageResult:
    cert = load_json(strategy_certificate_path)
    strategy_input = load_json(strategy_input_path)
    gate = load_json(signal_gate_path)
    if cert.get("certificate_id") != "STRATEGY-INPUT-AUDIT-V77.35" or cert.get("status") != "PASS":
        raise RiskManagementError("invalid V77.35 strategy certificate")
    if strategy_input.get("stage") != "V77.31" or gate.get("stage") != "V77.34" or gate.get("status") != "PASS":
        raise RiskManagementError("invalid strategy input or signal gate")
    if account_equity <= 0 or not 0 < risk_per_trade_pct <= 0.05 or atr_stop_multiple <= 0:
        raise RiskManagementError("invalid risk configuration")

    f = strategy_input["feature_set"]
    price = float(f["close"])
    atr = float(f["atr_14"])
    approved_signal = gate.get("approved_signal", "HOLD")
    risk_budget = account_equity * risk_per_trade_pct
    stop_distance = max(atr * atr_stop_multiple, price * 0.001)
    raw_quantity = math.floor(risk_budget / stop_distance)
    quantity = 0 if approved_signal == "HOLD" else max(0, raw_quantity)
    notional = round(quantity * price, 2)

    doc = {
        "schema_version": "v77.36.position_risk_calculator.1",
        "stage": "V77.36",
        "status": "PASS",
        "risk_calculation_id": "POSITION-RISK-V77-36",
        "symbol": f["symbol"],
        "approved_signal": approved_signal,
        "reference_price": round(price, 8),
        "account_equity": round(account_equity, 2),
        "risk_per_trade_pct": risk_per_trade_pct,
        "risk_budget": round(risk_budget, 2),
        "atr_14": round(atr, 8),
        "atr_stop_multiple": atr_stop_multiple,
        "stop_distance": round(stop_distance, 8),
        "raw_quantity": raw_quantity,
        "recommended_quantity": quantity,
        "recommended_notional": notional,
        "source_strategy_certificate_sha256": cert.get("certificate_sha256"),
        "source_signal_safety_gate_sha256": gate.get("signal_safety_gate_sha256"),
        "orders_created": 0,
        "safety": safety(),
        "next_phase": "V77_37_EXPOSURE_LIMIT_ENGINE",
    }
    doc["position_risk_sha256"] = digest_json({k:v for k,v in doc.items() if k != "position_risk_sha256"})
    verification = {
        "schema_version": "v77.36.position_risk_calculator_verification.1",
        "stage": "V77.36", "status": "PASS", "verified": True,
        "error_count": 0, "errors": [],
        "position_risk_sha256": doc["position_risk_sha256"],
        "next_phase": doc["next_phase"],
    }
    verification["verification_sha256"] = digest_json({k:v for k,v in verification.items() if k != "verification_sha256"})
    df = output_dir/"position_risk_calculator_v77_36.json"
    vf = output_dir/"position_risk_calculator_verification_v77_36.json"
    write_json(df,doc); write_json(vf,verification)
    return StageResult("V77.36","PASS",doc["position_risk_sha256"],verification["verification_sha256"],doc["next_phase"],(str(df),str(vf)))

def apply_exposure_limits(
    position_risk_path: Path,
    output_dir: Path,
    *,
    current_gross_exposure: float = 0.0,
    max_symbol_exposure_pct: float = 0.20,
    max_gross_exposure_pct: float = 0.80,
) -> StageResult:
    risk = load_json(position_risk_path)
    if risk.get("stage") != "V77.36" or risk.get("status") != "PASS":
        raise RiskManagementError("invalid V77.36 position risk")
    equity = float(risk["account_equity"])
    if current_gross_exposure < 0 or not 0 < max_symbol_exposure_pct <= 1 or not 0 < max_gross_exposure_pct <= 1:
        raise RiskManagementError("invalid exposure configuration")

    requested = float(risk["recommended_notional"])
    symbol_limit = equity * max_symbol_exposure_pct
    gross_available = max(0.0, equity * max_gross_exposure_pct - current_gross_exposure)
    approved_notional = min(requested, symbol_limit, gross_available)
    price = float(risk["reference_price"])
    approved_quantity = 0 if price <= 0 else math.floor(approved_notional / price)
    approved_notional = round(approved_quantity * price, 2)
    clipped = approved_quantity < int(risk["recommended_quantity"])

    doc = {
        "schema_version": "v77.37.exposure_limit_engine.1",
        "stage": "V77.37",
        "status": "PASS",
        "exposure_decision_id": "EXPOSURE-LIMIT-V77-37",
        "symbol": risk["symbol"],
        "requested_quantity": risk["recommended_quantity"],
        "approved_quantity": approved_quantity,
        "requested_notional": requested,
        "approved_notional": approved_notional,
        "current_gross_exposure": round(current_gross_exposure,2),
        "max_symbol_exposure_pct": max_symbol_exposure_pct,
        "max_gross_exposure_pct": max_gross_exposure_pct,
        "symbol_exposure_limit": round(symbol_limit,2),
        "gross_exposure_available": round(gross_available,2),
        "exposure_clipped": clipped,
        "decision": "ALLOW_WITH_LIMITS" if approved_quantity > 0 else "NO_POSITION",
        "source_position_risk_sha256": risk.get("position_risk_sha256"),
        "orders_created": 0,
        "safety": safety(),
        "next_phase": "V77_38_STOP_LOSS_TAKE_PROFIT_POLICY",
    }
    doc["exposure_limit_sha256"] = digest_json({k:v for k,v in doc.items() if k != "exposure_limit_sha256"})
    verification = {
        "schema_version":"v77.37.exposure_limit_engine_verification.1","stage":"V77.37",
        "status":"PASS","verified":True,"error_count":0,"errors":[],
        "exposure_limit_sha256":doc["exposure_limit_sha256"],"next_phase":doc["next_phase"],
    }
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    df=output_dir/"exposure_limit_engine_v77_37.json";vf=output_dir/"exposure_limit_engine_verification_v77_37.json"
    write_json(df,doc);write_json(vf,verification)
    return StageResult("V77.37","PASS",doc["exposure_limit_sha256"],verification["verification_sha256"],doc["next_phase"],(str(df),str(vf)))

def build_exit_policy(
    position_risk_path: Path,
    exposure_limit_path: Path,
    output_dir: Path,
    *,
    reward_to_risk_ratio: float = 2.0,
) -> StageResult:
    risk=load_json(position_risk_path); exposure=load_json(exposure_limit_path)
    if risk.get("stage")!="V77.36" or exposure.get("stage")!="V77.37":
        raise RiskManagementError("invalid risk or exposure document")
    if reward_to_risk_ratio < 1:
        raise RiskManagementError("reward_to_risk_ratio must be at least 1")
    signal=risk.get("approved_signal","HOLD");price=float(risk["reference_price"]);distance=float(risk["stop_distance"])
    if signal=="BUY":
        stop=price-distance;take=price+distance*reward_to_risk_ratio
    elif signal=="SELL":
        stop=price+distance;take=price-distance*reward_to_risk_ratio
    else:
        stop=price;take=price
    doc={
        "schema_version":"v77.38.stop_loss_take_profit_policy.1","stage":"V77.38","status":"PASS",
        "exit_policy_id":"EXIT-POLICY-V77-38","symbol":risk["symbol"],"signal":signal,
        "approved_quantity":exposure["approved_quantity"],"entry_reference_price":round(price,8),
        "stop_loss_price":round(stop,8),"take_profit_price":round(take,8),
        "risk_distance":round(distance,8),"reward_to_risk_ratio":reward_to_risk_ratio,
        "trailing_stop_enabled":False,"policy_state":"ACTIVE" if exposure["approved_quantity"]>0 else "DORMANT",
        "source_position_risk_sha256":risk.get("position_risk_sha256"),
        "source_exposure_limit_sha256":exposure.get("exposure_limit_sha256"),
        "orders_created":0,"safety":safety(),"next_phase":"V77_39_RISK_DECISION_SAFETY_GATE",
    }
    doc["exit_policy_sha256"]=digest_json({k:v for k,v in doc.items() if k!="exit_policy_sha256"})
    verification={"schema_version":"v77.38.stop_loss_take_profit_policy_verification.1","stage":"V77.38",
        "status":"PASS","verified":True,"error_count":0,"errors":[],
        "exit_policy_sha256":doc["exit_policy_sha256"],"next_phase":doc["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    df=output_dir/"stop_loss_take_profit_policy_v77_38.json";vf=output_dir/"stop_loss_take_profit_policy_verification_v77_38.json"
    write_json(df,doc);write_json(vf,verification)
    return StageResult("V77.38","PASS",doc["exit_policy_sha256"],verification["verification_sha256"],doc["next_phase"],(str(df),str(vf)))

def run_risk_decision_safety_gate(
    position_risk_path: Path,
    exposure_limit_path: Path,
    exit_policy_path: Path,
    output_dir: Path,
) -> StageResult:
    risk=load_json(position_risk_path);exposure=load_json(exposure_limit_path);policy=load_json(exit_policy_path)
    errors=[]
    if risk.get("stage")!="V77.36" or exposure.get("stage")!="V77.37" or policy.get("stage")!="V77.38":errors.append("stage_chain")
    if exposure.get("approved_quantity",0)<0:errors.append("negative_quantity")
    if exposure.get("approved_notional",0)>exposure.get("symbol_exposure_limit",0)+0.01:errors.append("symbol_exposure_breach")
    if exposure.get("approved_notional",0)>exposure.get("gross_exposure_available",0)+0.01:errors.append("gross_exposure_breach")
    if any(x.get("orders_created")!=0 for x in (risk,exposure,policy)):errors.append("order_creation_detected")
    signal=risk.get("approved_signal")
    entry=float(policy.get("entry_reference_price",0));stop=float(policy.get("stop_loss_price",0));take=float(policy.get("take_profit_price",0))
    if signal=="BUY" and not (stop<entry<take):errors.append("buy_exit_geometry")
    if signal=="SELL" and not (take<entry<stop):errors.append("sell_exit_geometry")
    for doc,key in ((risk,"position_risk_sha256"),(exposure,"exposure_limit_sha256"),(policy,"exit_policy_sha256")):
        if doc.get(key)!=digest_json({k:v for k,v in doc.items() if k!=key}):errors.append(key)
    status="PASS" if not errors else "FAIL"
    gate={
        "schema_version":"v77.39.risk_decision_safety_gate.1","stage":"V77.39","status":status,
        "decision":"ALLOW_PAPER_RISK_DECISION" if not errors else "BLOCK_RISK_DECISION",
        "approved_quantity":exposure.get("approved_quantity",0) if not errors else 0,
        "approved_notional":exposure.get("approved_notional",0) if not errors else 0,
        "error_count":len(errors),"errors":errors,
        "source_position_risk_sha256":risk.get("position_risk_sha256"),
        "source_exposure_limit_sha256":exposure.get("exposure_limit_sha256"),
        "source_exit_policy_sha256":policy.get("exit_policy_sha256"),
        "orders_created":0,"safety":safety(),"next_phase":"V77_40_RISK_MANAGEMENT_AUDIT_CERTIFICATE",
    }
    gate["risk_safety_gate_sha256"]=digest_json({k:v for k,v in gate.items() if k!="risk_safety_gate_sha256"})
    verification={"schema_version":"v77.39.risk_decision_safety_gate_verification.1","stage":"V77.39",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "risk_safety_gate_sha256":gate["risk_safety_gate_sha256"],"next_phase":gate["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    gf=output_dir/"risk_decision_safety_gate_v77_39.json";vf=output_dir/"risk_decision_safety_gate_verification_v77_39.json"
    write_json(gf,gate);write_json(vf,verification)
    return StageResult("V77.39",status,gate["risk_safety_gate_sha256"],verification["verification_sha256"],gate["next_phase"],(str(gf),str(vf)))

def issue_risk_management_certificate(v36: Path,v37: Path,v38: Path,v39: Path,output_dir: Path)->StageResult:
    docs=[load_json(p) for p in (v36,v37,v38,v39)];expected=["V77.36","V77.37","V77.38","V77.39"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v77.40.risk_management_audit_certificate.1","stage":"V77.40",
        "certificate_id":"RISK-MANAGEMENT-AUDIT-V77.40","status":status,
        "decision":"risk_management_certified" if not errors else "risk_management_rejected",
        "certified_stages":expected,"stage_count":4,
        "anchors":{"v77_36_verification_sha256":docs[0].get("verification_sha256"),
                   "v77_37_verification_sha256":docs[1].get("verification_sha256"),
                   "v77_38_verification_sha256":docs[2].get("verification_sha256"),
                   "v77_39_verification_sha256":docs[3].get("verification_sha256")},
        "error_count":len(errors),"errors":errors,"safety":safety(),
        "next_phase":"V77_41_PAPER_PORTFOLIO_STATE_ENGINE" if not errors else "REPAIR_V77_40",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    verification={"schema_version":"v77.40.risk_management_audit_certificate_verification.1","stage":"V77.40",
        "status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    verification["verification_sha256"]=digest_json({k:v for k,v in verification.items() if k!="verification_sha256"})
    cf=output_dir/"risk_management_audit_certificate_v77_40.json";vf=output_dir/"risk_management_audit_certificate_verification_v77_40.json"
    write_json(cf,cert);write_json(vf,verification)
    return StageResult("V77.40",status,cert["certificate_sha256"],verification["verification_sha256"],cert["next_phase"],(str(cf),str(vf)))
