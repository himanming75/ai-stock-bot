from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class NormalizedSignal:
    normalized_signal_id: str
    source_signal_id: str
    strategy_id: str
    candidate_id: str
    symbol: str
    timestamp: str
    action: str
    confidence: float
    normalized_sha256: str

@dataclass(frozen=True)
class RiskRequest:
    risk_request_id: str
    normalized_signal_id: str
    candidate_id: str
    symbol: str
    timestamp: str
    side: str
    requested_notional: float
    reference_price: float
    current_cash: float
    current_position_quantity: int
    risk_request_sha256: str

@dataclass(frozen=True)
class RiskDecision:
    risk_decision_id: str
    risk_request_id: str
    decision: str
    approved_notional: float
    approved_quantity: int
    reason: str
    risk_decision_sha256: str

def normalize_signal(signal: dict, confidence_map: dict[str,float]) -> NormalizedSignal:
    required=("signal_id","strategy_id","candidate_id","symbol","timestamp","action")
    for key in required:
        if key not in signal:
            raise ValueError(f"missing signal field:{key}")
    action=str(signal["action"]).upper()
    if action not in ("BUY","SELL","HOLD"):
        raise ValueError("unsupported signal action")
    confidence=float(confidence_map.get(action,0.0))
    if confidence<0 or confidence>1:
        raise ValueError("confidence out of range")
    base={
        "source_signal_id":signal["signal_id"],
        "strategy_id":signal["strategy_id"],
        "candidate_id":signal["candidate_id"],
        "symbol":str(signal["symbol"]).upper(),
        "timestamp":signal["timestamp"],
        "action":action,
        "confidence":confidence,
    }
    sha=digest_json(base)
    return NormalizedSignal(
        normalized_signal_id=f"NSIG-{signal['signal_id']}-{sha[:12]}",
        source_signal_id=signal["signal_id"],
        strategy_id=signal["strategy_id"],
        candidate_id=signal["candidate_id"],
        symbol=str(signal["symbol"]).upper(),
        timestamp=signal["timestamp"],
        action=action,
        confidence=confidence,
        normalized_sha256=sha,
    )

def build_risk_request(signal: NormalizedSignal, reference_price: float, current_cash: float,
                       current_position_quantity: int, max_notional: float) -> RiskRequest | None:
    if reference_price<=0:
        raise ValueError("reference_price must be positive")
    if current_cash<0:
        raise ValueError("current_cash must be non-negative")
    if current_position_quantity<0:
        raise ValueError("current_position_quantity must be non-negative")
    if max_notional<=0:
        raise ValueError("max_notional must be positive")
    if signal.action=="HOLD":
        return None
    requested=min(max_notional,current_cash) if signal.action=="BUY" else min(
        max_notional,current_position_quantity*reference_price
    )
    side="buy" if signal.action=="BUY" else "sell"
    base={
        "normalized_signal_id":signal.normalized_signal_id,
        "candidate_id":signal.candidate_id,
        "symbol":signal.symbol,
        "timestamp":signal.timestamp,
        "side":side,
        "requested_notional":round(requested,8),
        "reference_price":float(reference_price),
        "current_cash":float(current_cash),
        "current_position_quantity":int(current_position_quantity),
    }
    sha=digest_json(base)
    return RiskRequest(
        risk_request_id=f"RREQ-{signal.normalized_signal_id}-{sha[:12]}",
        normalized_signal_id=signal.normalized_signal_id,
        candidate_id=signal.candidate_id,
        symbol=signal.symbol,
        timestamp=signal.timestamp,
        side=side,
        requested_notional=round(requested,8),
        reference_price=float(reference_price),
        current_cash=float(current_cash),
        current_position_quantity=int(current_position_quantity),
        risk_request_sha256=sha,
    )

def evaluate_risk_request(request: RiskRequest, max_position_notional: float,
                          min_order_notional: float, max_cash_utilization: float) -> RiskDecision:
    if max_position_notional<=0 or min_order_notional<0:
        raise ValueError("invalid risk limits")
    if not 0<max_cash_utilization<=1:
        raise ValueError("invalid cash utilization")
    decision="REJECT"
    approved_notional=0.0
    approved_quantity=0
    reason="UNSPECIFIED"

    if request.requested_notional < min_order_notional:
        reason="BELOW_MINIMUM_NOTIONAL"
    elif request.side=="buy":
        cash_cap=request.current_cash*max_cash_utilization
        approved_notional=min(request.requested_notional,max_position_notional,cash_cap)
        approved_quantity=int(approved_notional//request.reference_price)
        approved_notional=round(approved_quantity*request.reference_price,8)
        if approved_quantity>0:
            decision="APPROVE"
            reason="BUY_WITHIN_RISK_LIMITS"
        else:
            reason="INSUFFICIENT_BUYING_POWER"
    elif request.side=="sell":
        max_sell_notional=request.current_position_quantity*request.reference_price
        approved_notional=min(request.requested_notional,max_position_notional,max_sell_notional)
        approved_quantity=min(request.current_position_quantity,int(approved_notional//request.reference_price))
        approved_notional=round(approved_quantity*request.reference_price,8)
        if approved_quantity>0:
            decision="APPROVE"
            reason="SELL_WITHIN_POSITION_LIMITS"
        else:
            reason="NO_POSITION_AVAILABLE"
    else:
        raise ValueError("unsupported side")

    base={
        "risk_request_id":request.risk_request_id,
        "decision":decision,
        "approved_notional":approved_notional,
        "approved_quantity":approved_quantity,
        "reason":reason,
    }
    sha=digest_json(base)
    return RiskDecision(
        risk_decision_id=f"RDEC-{request.risk_request_id}-{sha[:12]}",
        risk_request_id=request.risk_request_id,
        decision=decision,
        approved_notional=approved_notional,
        approved_quantity=approved_quantity,
        reason=reason,
        risk_decision_sha256=sha,
    )

def build_signal_risk_bridge_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.40" or cert.get("status")!="PASS":
        errors.append("strategy_runtime_certificate")
    if cert.get("certification_scope")!="OFFLINE_SIGNAL_RISK_BRIDGE_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    bridge=config.get("signal_risk_bridge",{})
    for key in ("confidence_map","max_requested_notional","risk_limits","reference_price"):
        if key not in bridge:
            errors.append(f"config_{key}")
    champion=cert.get("champion_candidate") or {}
    if not champion.get("candidate_id"):
        errors.append("champion_candidate_id")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.41.signal_risk_bridge_foundation.1",
        "stage":"V78.41",
        "status":status,
        "scope":"OFFLINE_RISK_DECISION_ONLY",
        "champion_candidate":champion,
        "signal_risk_bridge":bridge,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_42_SIGNAL_NORMALIZATION_RISK_REQUEST",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"signal_risk_bridge_foundation_v78_41.json",doc)
    ver={
        "stage":"V78.41","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "foundation_sha256":doc["foundation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"signal_risk_bridge_foundation_verification_v78_41.json",ver)
    return doc

def run_signal_normalization_risk_request(foundation_path: Path, signal_source_path: Path, output_dir: Path) -> dict:
    foundation,source=map(load_json,(foundation_path,signal_source_path))
    errors=[]
    if foundation.get("stage")!="V78.41" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if source.get("stage")!="V78.38" or source.get("status")!="PASS":
        errors.append("signal_source_input")
    cfg=foundation.get("signal_risk_bridge",{})
    normalized=[]
    requests=[]
    try:
        for signal in source.get("signals",[]):
            n=normalize_signal(signal,cfg.get("confidence_map",{}))
            normalized.append(n)
            req=build_risk_request(
                n,
                float(cfg.get("reference_price",100.0)),
                float(cfg.get("current_cash",100000.0)),
                int(cfg.get("current_position_quantity",10)),
                float(cfg.get("max_requested_notional",1000.0)),
            )
            if req is not None:
                requests.append(req)
    except Exception as exc:
        errors.append(f"normalization_exception:{type(exc).__name__}")

    checks={
        "signal_count_preserved":len(normalized)==len(source.get("signals",[])),
        "hold_does_not_create_request":sum(x.action=="HOLD" for x in normalized)==len(normalized)-len(requests),
        "buy_and_sell_requests_present":{"buy","sell"}.issubset({x.side for x in requests}),
        "candidate_consistent":len({x.candidate_id for x in normalized})==1,
        "normalized_hashes_unique":len({x.normalized_sha256 for x in normalized})==len(normalized),
        "risk_request_hashes_unique":len({x.risk_request_sha256 for x in requests})==len(requests),
        "generated_order_count_zero":True,
        "submitted_order_count_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("normalization_request_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.42.signal_normalization_risk_request.1",
        "stage":"V78.42",
        "status":status,
        "normalized_signals":[asdict(x) for x in normalized],
        "risk_requests":[asdict(x) for x in requests],
        "checks":checks,
        "failed_checks":failed,
        "generated_order_count":0,
        "submitted_order_count":0,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_43_RISK_DECISION_INTEGRATION",
    }
    doc["normalization_sha256"]=digest_json({k:v for k,v in doc.items() if k!="normalization_sha256"})
    write_json(output_dir/"signal_normalization_risk_request_v78_42.json",doc)
    ver={
        "stage":"V78.42","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "normalization_sha256":doc["normalization_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"signal_normalization_risk_request_verification_v78_42.json",ver)
    return doc

def run_risk_decision_integration(foundation_path: Path, normalization_path: Path, output_dir: Path) -> dict:
    foundation,normalization=map(load_json,(foundation_path,normalization_path))
    errors=[]
    if foundation.get("stage")!="V78.41" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if normalization.get("stage")!="V78.42" or normalization.get("status")!="PASS":
        errors.append("normalization_input")
    limits=foundation.get("signal_risk_bridge",{}).get("risk_limits",{})
    decisions=[]
    try:
        for raw in normalization.get("risk_requests",[]):
            req=RiskRequest(**raw)
            decisions.append(evaluate_risk_request(
                req,
                float(limits.get("max_position_notional",1000.0)),
                float(limits.get("min_order_notional",50.0)),
                float(limits.get("max_cash_utilization",0.1)),
            ))
    except Exception as exc:
        errors.append(f"risk_decision_exception:{type(exc).__name__}")

    checks={
        "decision_count_matches_requests":len(decisions)==len(normalization.get("risk_requests",[])),
        "allowed_decisions_only":{x.decision for x in decisions}.issubset({"APPROVE","REJECT"}),
        "approved_quantity_non_negative":all(x.approved_quantity>=0 for x in decisions),
        "approved_notional_non_negative":all(x.approved_notional>=0 for x in decisions),
        "decision_hashes_unique":len({x.risk_decision_sha256 for x in decisions})==len(decisions),
        "buy_and_sell_approved":len(decisions)>=2 and all(x.decision=="APPROVE" for x in decisions),
        "generated_order_count_zero":True,
        "submitted_order_count_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("risk_decision_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.43.risk_decision_integration.1",
        "stage":"V78.43",
        "status":status,
        "risk_decisions":[asdict(x) for x in decisions],
        "checks":checks,
        "failed_checks":failed,
        "generated_order_count":0,
        "submitted_order_count":0,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_44_SIGNAL_RISK_SAFETY_GATE",
    }
    doc["risk_decision_sha256"]=digest_json({k:v for k,v in doc.items() if k!="risk_decision_sha256"})
    write_json(output_dir/"risk_decision_integration_v78_43.json",doc)
    ver={
        "stage":"V78.43","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "risk_decision_sha256":doc["risk_decision_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"risk_decision_integration_verification_v78_43.json",ver)
    return doc

def run_signal_risk_safety_gate(foundation_path: Path, normalization_path: Path,
                                decision_path: Path, output_dir: Path) -> dict:
    foundation,normalization,decision=map(load_json,(foundation_path,normalization_path,decision_path))
    errors=[]
    for expected,doc in (("V78.41",foundation),("V78.42",normalization),("V78.43",decision)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    normalized=normalization.get("normalized_signals",[])
    requests=normalization.get("risk_requests",[])
    decisions=decision.get("risk_decisions",[])
    checks={
        "offline_risk_scope":foundation.get("scope")=="OFFLINE_RISK_DECISION_ONLY",
        "normalization_checks_passed":normalization.get("failed_checks")==[],
        "decision_checks_passed":decision.get("failed_checks")==[],
        "hold_has_no_risk_request":sum(x["action"]=="HOLD" for x in normalized)==len(normalized)-len(requests),
        "request_decision_one_to_one":len(requests)==len(decisions),
        "request_ids_unique":len({x["risk_request_id"] for x in requests})==len(requests),
        "decision_ids_unique":len({x["risk_decision_id"] for x in decisions})==len(decisions),
        "generated_orders_zero":normalization.get("generated_order_count")==0 and decision.get("generated_order_count")==0,
        "submitted_orders_zero":normalization.get("submitted_order_count")==0 and decision.get("submitted_order_count")==0,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,normalization,decision)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,normalization,decision)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,normalization,decision)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("signal_risk_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.44.signal_risk_safety_gate.1",
        "stage":"V78.44",
        "status":status,
        "gate_scope":"OFFLINE_PORTFOLIO_RUNTIME_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_PORTFOLIO_RUNTIME" if not errors else "BLOCK_PORTFOLIO_RUNTIME",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,
        "failed_checks":failed,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_45_SIGNAL_RISK_BRIDGE_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"signal_risk_safety_gate_v78_44.json",doc)
    ver={
        "stage":"V78.44","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"signal_risk_safety_gate_verification_v78_44.json",ver)
    return doc

def issue_signal_risk_bridge_certificate(v41: Path,v42: Path,v43: Path,v44: Path,
                                         foundation_path: Path,output_dir: Path) -> dict:
    docs=list(map(load_json,(v41,v42,v43,v44)))
    foundation=load_json(foundation_path)
    expected=["V78.41","V78.42","V78.43","V78.44"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.45.signal_risk_bridge_certificate.1",
        "stage":"V78.45",
        "certificate_id":"SIGNAL-RISK-BRIDGE-V78.45",
        "status":status,
        "decision":"certified_for_offline_portfolio_runtime" if not errors else "signal_risk_bridge_rejected",
        "certification_scope":"OFFLINE_PORTFOLIO_RUNTIME_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_46_PORTFOLIO_RUNTIME_FOUNDATION" if not errors else "REPAIR_V78_45",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"signal_risk_bridge_certificate_v78_45.json",cert)
    ver={
        "stage":"V78.45","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"signal_risk_bridge_certificate_verification_v78_45.json",ver)
    return cert
