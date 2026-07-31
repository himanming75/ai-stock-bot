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
class AuditRecord:
    sequence: int
    record_type: str
    source_id: str
    source_sha256: str
    previous_record_sha256: str
    record_sha256: str

def build_audit_record(sequence:int, record_type:str, source_id:str,
                       source_sha256:str, previous_record_sha256:str)->AuditRecord:
    if sequence <= 0:
        raise ValueError("sequence must be positive")
    if not record_type or not source_id or not source_sha256:
        raise ValueError("audit record fields required")
    base = {
        "sequence":sequence,
        "record_type":record_type,
        "source_id":source_id,
        "source_sha256":source_sha256,
        "previous_record_sha256":previous_record_sha256,
    }
    return AuditRecord(
        sequence=sequence,
        record_type=record_type,
        source_id=source_id,
        source_sha256=source_sha256,
        previous_record_sha256=previous_record_sha256,
        record_sha256=digest_json(base),
    )

def verify_audit_chain(records:list[AuditRecord])->bool:
    previous=""
    expected_sequence=1
    seen=set()
    for record in records:
        if record.sequence != expected_sequence:
            raise ValueError("audit sequence gap")
        if record.source_id in seen:
            raise ValueError("duplicate audit source")
        if record.previous_record_sha256 != previous:
            raise ValueError("audit chain linkage mismatch")
        expected=digest_json({
            "sequence":record.sequence,
            "record_type":record.record_type,
            "source_id":record.source_id,
            "source_sha256":record.source_sha256,
            "previous_record_sha256":record.previous_record_sha256,
        })
        if expected != record.record_sha256:
            raise ValueError("audit record hash mismatch")
        seen.add(record.source_id)
        previous=record.record_sha256
        expected_sequence += 1
    return True

def reconstruct_expected_state(starting_cash:float, fills:list[dict])->dict:
    cash=float(starting_cash)
    realized=0.0
    positions:dict[str,dict[str,float|int]]={}
    total_commission=0.0
    total_slippage=0.0
    for fill in fills:
        symbol=str(fill["symbol"]).upper()
        side=str(fill["side"]).lower()
        qty=int(fill["quantity"])
        price=float(fill["price"])
        commission=float(fill["commission"])
        slippage=float(fill["slippage_cost"])
        gross=float(fill["gross_notional"])
        total_commission=round(total_commission+commission,8)
        total_slippage=round(total_slippage+slippage,8)
        if side=="buy":
            old=positions.get(symbol,{"quantity":0,"average_cost":0.0})
            old_qty=int(old["quantity"])
            old_avg=float(old["average_cost"])
            new_qty=old_qty+qty
            avg=((old_qty*old_avg)+gross+commission)/new_qty
            cash=round(cash-gross-commission,8)
            positions[symbol]={"quantity":new_qty,"average_cost":round(avg,8)}
        elif side=="sell":
            old=positions.get(symbol)
            if old is None or int(old["quantity"])<qty:
                raise ValueError("audit oversell")
            old_qty=int(old["quantity"])
            old_avg=float(old["average_cost"])
            realized_delta=round((price-old_avg)*qty-commission,8)
            cash=round(cash+gross-commission,8)
            realized=round(realized+realized_delta,8)
            new_qty=old_qty-qty
            if new_qty==0:
                del positions[symbol]
            else:
                positions[symbol]={"quantity":new_qty,"average_cost":old_avg}
        else:
            raise ValueError("unsupported fill side")
    return {
        "cash":cash,
        "realized_pnl":realized,
        "positions":[{"symbol":k,**positions[k]} for k in sorted(positions)],
        "total_commission":total_commission,
        "total_slippage":total_slippage,
    }

def build_audit_reconciliation_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.65" or cert.get("status")!="PASS":
        errors.append("fill_portfolio_certificate")
    if cert.get("certification_scope")!="OFFLINE_AUDIT_RECONCILIATION_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    audit=config.get("audit_reconciliation",{})
    for key in ("cash_tolerance","pnl_tolerance","position_tolerance","allow_real_broker_sources"):
        if key not in audit:
            errors.append(f"config_{key}")
    if audit.get("allow_real_broker_sources") is not False:
        errors.append("real_broker_sources")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.66.audit_reconciliation_foundation.1",
        "stage":"V78.66","status":status,
        "scope":"OFFLINE_LEDGER_AUDIT_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "audit_reconciliation":audit,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_67_CASH_POSITION_FILL_CROSS_CHECK",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"audit_reconciliation_foundation_v78_66.json",doc)
    ver={"stage":"V78.66","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"audit_reconciliation_foundation_verification_v78_66.json",ver)
    return doc

def run_cash_position_fill_cross_check(foundation_path:Path,normalization_path:Path,
                                       reconciliation_path:Path,output_dir:Path)->dict:
    foundation,normalization,reconciliation=map(load_json,(foundation_path,normalization_path,reconciliation_path))
    errors=[]
    if foundation.get("stage")!="V78.66" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if normalization.get("stage")!="V78.62" or normalization.get("status")!="PASS":
        errors.append("normalization_input")
    if reconciliation.get("stage")!="V78.63" or reconciliation.get("status")!="PASS":
        errors.append("reconciliation_input")
    cfg=foundation.get("audit_reconciliation",{})
    starting_cash=float(cfg.get("starting_cash",100000.0))
    try:
        expected=reconstruct_expected_state(starting_cash,normalization.get("normalized_fills",[]))
        snapshot=reconciliation.get("portfolio_snapshot",{})
    except Exception as exc:
        expected={};snapshot={}
        errors.append(f"cross_check_exception:{type(exc).__name__}")

    actual_positions=[
        {"symbol":x["symbol"],"quantity":x["quantity"],"average_cost":x["average_cost"]}
        for x in snapshot.get("positions",[])
    ]
    cash_delta=round(abs(float(snapshot.get("cash",0))-float(expected.get("cash",0))),8)
    pnl_delta=round(abs(float(snapshot.get("realized_pnl",0))-float(expected.get("realized_pnl",0))),8)
    checks={
        "cash_within_tolerance":cash_delta<=float(cfg.get("cash_tolerance",0.000001)),
        "realized_pnl_within_tolerance":pnl_delta<=float(cfg.get("pnl_tolerance",0.000001)),
        "positions_match":actual_positions==expected.get("positions",[]),
        "event_count_matches_fill_count":snapshot.get("event_count")==len(normalization.get("normalized_fills",[])),
        "commission_matches":reconciliation.get("total_commission")==expected.get("total_commission"),
        "flat_portfolio_consistent":snapshot.get("positions",[])==[] and snapshot.get("market_value")==0.0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("cross_check_failed")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.67.cash_position_fill_cross_check.1",
        "stage":"V78.67","status":status,
        "expected_state":expected,
        "actual_snapshot":snapshot,
        "cash_delta":cash_delta,
        "realized_pnl_delta":pnl_delta,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_68_LEDGER_INTEGRITY_REPLAY_AUDIT",
    }
    doc["cross_check_sha256"]=digest_json({k:v for k,v in doc.items() if k!="cross_check_sha256"})
    write_json(output_dir/"cash_position_fill_cross_check_v78_67.json",doc)
    ver={"stage":"V78.67","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "cross_check_sha256":doc["cross_check_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"cash_position_fill_cross_check_verification_v78_67.json",ver)
    return doc

def run_ledger_integrity_replay_audit(normalization_path:Path,reconciliation_path:Path,output_dir:Path)->dict:
    normalization,reconciliation=map(load_json,(normalization_path,reconciliation_path))
    errors=[]
    if normalization.get("stage")!="V78.62" or normalization.get("status")!="PASS":
        errors.append("normalization_input")
    if reconciliation.get("stage")!="V78.63" or reconciliation.get("status")!="PASS":
        errors.append("reconciliation_input")

    records=[]
    previous=""
    try:
        sources=[]
        for fill in normalization.get("normalized_fills",[]):
            sources.append(("NORMALIZED_FILL",fill["normalized_fill_id"],fill["normalized_sha256"]))
        for event in reconciliation.get("portfolio_fill_events",[]):
            sources.append(("PORTFOLIO_FILL_EVENT",event["normalized_fill_id"],event["event_sha256"]))
        for idx,(rtype,sid,sha) in enumerate(sources,1):
            unique_id=f"{rtype}:{sid}"
            record=build_audit_record(idx,rtype,unique_id,sha,previous)
            records.append(record)
            previous=record.record_sha256
        chain_verified=verify_audit_chain(records)
    except Exception as exc:
        chain_verified=False
        errors.append(f"audit_chain_exception:{type(exc).__name__}")

    replay=reconciliation.get("replay_state",{})
    snapshot=reconciliation.get("portfolio_snapshot",{})
    checks={
        "audit_chain_verified":chain_verified,
        "audit_sequence_contiguous":[x.sequence for x in records]==list(range(1,len(records)+1)),
        "audit_record_hashes_unique":len({x.record_sha256 for x in records})==len(records),
        "source_hashes_present":all(bool(x.source_sha256) for x in records),
        "replay_cash_matches_snapshot":replay.get("cash")==snapshot.get("cash"),
        "replay_realized_matches_snapshot":replay.get("realized_pnl")==snapshot.get("realized_pnl"),
        "audit_record_count_expected":len(records)==(
            len(normalization.get("normalized_fills",[]))+
            len(reconciliation.get("portfolio_fill_events",[]))
        ),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("ledger_audit_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.68.ledger_integrity_replay_audit.1",
        "stage":"V78.68","status":status,
        "audit_records":[asdict(x) for x in records],
        "audit_chain_head":records[-1].record_sha256 if records else "",
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_69_AUDIT_RECONCILIATION_SAFETY_GATE",
    }
    doc["audit_sha256"]=digest_json({k:v for k,v in doc.items() if k!="audit_sha256"})
    write_json(output_dir/"ledger_integrity_replay_audit_v78_68.json",doc)
    ver={"stage":"V78.68","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "audit_sha256":doc["audit_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"ledger_integrity_replay_audit_verification_v78_68.json",ver)
    return doc

def run_audit_reconciliation_safety_gate(foundation_path:Path,cross_check_path:Path,
                                         audit_path:Path,output_dir:Path)->dict:
    foundation,cross_check,audit=map(load_json,(foundation_path,cross_check_path,audit_path))
    errors=[]
    for expected,doc in (("V78.66",foundation),("V78.67",cross_check),("V78.68",audit)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    records=audit.get("audit_records",[])
    checks={
        "offline_audit_scope":foundation.get("scope")=="OFFLINE_LEDGER_AUDIT_ONLY",
        "cross_check_passed":cross_check.get("failed_checks")==[],
        "ledger_audit_passed":audit.get("failed_checks")==[],
        "cash_delta_zero":cross_check.get("cash_delta")==0.0,
        "realized_pnl_delta_zero":cross_check.get("realized_pnl_delta")==0.0,
        "audit_chain_non_empty":len(records)>0,
        "audit_sequence_contiguous":[x["sequence"] for x in records]==list(range(1,len(records)+1)),
        "real_broker_sources_disabled":foundation.get("audit_reconciliation",{}).get("allow_real_broker_sources") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,cross_check,audit)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,cross_check,audit)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,cross_check,audit)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("audit_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.69.audit_reconciliation_safety_gate.1",
        "stage":"V78.69","status":status,
        "gate_scope":"OFFLINE_PERFORMANCE_ACCOUNTING_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_PERFORMANCE_ACCOUNTING" if not errors else "BLOCK_PERFORMANCE_ACCOUNTING",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_70_AUDIT_RECONCILIATION_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"audit_reconciliation_safety_gate_v78_69.json",doc)
    ver={"stage":"V78.69","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"audit_reconciliation_safety_gate_verification_v78_69.json",ver)
    return doc

def issue_audit_reconciliation_certificate(v66:Path,v67:Path,v68:Path,v69:Path,
                                           foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v66,v67,v68,v69)))
    foundation=load_json(foundation_path)
    expected=["V78.66","V78.67","V78.68","V78.69"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.70.audit_reconciliation_certificate.1",
        "stage":"V78.70",
        "certificate_id":"AUDIT-RECONCILIATION-V78.70",
        "status":status,
        "decision":"certified_for_offline_performance_accounting" if not errors else "audit_reconciliation_rejected",
        "certification_scope":"OFFLINE_PERFORMANCE_ACCOUNTING_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_71_PERFORMANCE_ACCOUNTING_FOUNDATION" if not errors else "REPAIR_V78_70",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"audit_reconciliation_certificate_v78_70.json",cert)
    ver={"stage":"V78.70","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"audit_reconciliation_certificate_verification_v78_70.json",ver)
    return cert
