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
class NormalizedFill:
    normalized_fill_id: str
    source_fill_id: str
    broker_order_id: str
    order_intent_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    gross_notional: float
    commission: float
    slippage_cost: float
    remaining_quantity: int
    fill_status: str
    normalized_sha256: str

@dataclass(frozen=True)
class PortfolioFillEvent:
    sequence: int
    normalized_fill_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float
    cash_delta: float
    realized_pnl_delta: float
    event_sha256: str

def normalize_fill(fill: dict) -> NormalizedFill:
    required = (
        "fill_id","broker_order_id","order_intent_id","symbol","side",
        "fill_quantity","fill_price","gross_notional","commission",
        "slippage_cost","remaining_quantity","fill_status"
    )
    for key in required:
        if key not in fill:
            raise ValueError(f"missing fill field:{key}")
    side = str(fill["side"]).lower()
    if side not in ("buy","sell"):
        raise ValueError("unsupported fill side")
    quantity = int(fill["fill_quantity"])
    price = float(fill["fill_price"])
    gross = float(fill["gross_notional"])
    commission = float(fill["commission"])
    slippage = float(fill["slippage_cost"])
    remaining = int(fill["remaining_quantity"])
    if quantity <= 0 or price <= 0:
        raise ValueError("invalid fill quantity or price")
    if commission < 0 or slippage < 0 or remaining < 0:
        raise ValueError("invalid fill costs or remaining quantity")
    if round(quantity * price, 8) != round(gross, 8):
        raise ValueError("gross notional mismatch")
    base = {
        "source_fill_id":fill["fill_id"],
        "broker_order_id":fill["broker_order_id"],
        "order_intent_id":fill["order_intent_id"],
        "symbol":str(fill["symbol"]).upper(),
        "side":side,
        "quantity":quantity,
        "price":price,
        "gross_notional":round(gross,8),
        "commission":round(commission,8),
        "slippage_cost":round(slippage,8),
        "remaining_quantity":remaining,
        "fill_status":str(fill["fill_status"]),
    }
    sha = digest_json(base)
    return NormalizedFill(
        normalized_fill_id=f"NF-{fill['fill_id']}-{sha[:12]}",
        source_fill_id=fill["fill_id"],
        broker_order_id=fill["broker_order_id"],
        order_intent_id=fill["order_intent_id"],
        symbol=str(fill["symbol"]).upper(),
        side=side,
        quantity=quantity,
        price=price,
        gross_notional=round(gross,8),
        commission=round(commission,8),
        slippage_cost=round(slippage,8),
        remaining_quantity=remaining,
        fill_status=str(fill["fill_status"]),
        normalized_sha256=sha,
    )

class FillPortfolioRuntime:
    def __init__(self, starting_cash: float):
        if starting_cash < 0:
            raise ValueError("starting_cash must be non-negative")
        self.starting_cash=float(starting_cash)
        self.cash=float(starting_cash)
        self.realized_pnl=0.0
        self.positions:dict[str,dict[str,float|int]]={}
        self.events:list[PortfolioFillEvent]=[]
        self.sequence=0
        self.applied_fill_ids:set[str]=set()

    def apply(self, fill:NormalizedFill)->PortfolioFillEvent:
        if fill.normalized_fill_id in self.applied_fill_ids:
            raise ValueError("duplicate normalized fill")
        self.sequence += 1
        realized_delta=0.0
        if fill.side=="buy":
            total_cost=fill.gross_notional + fill.commission
            if total_cost > self.cash:
                raise ValueError("insufficient cash for fill")
            old=self.positions.get(fill.symbol,{"quantity":0,"average_cost":0.0})
            old_qty=int(old["quantity"])
            old_avg=float(old["average_cost"])
            new_qty=old_qty+fill.quantity
            new_avg=((old_qty*old_avg)+fill.gross_notional+fill.commission)/new_qty
            self.cash=round(self.cash-total_cost,8)
            self.positions[fill.symbol]={
                "quantity":new_qty,
                "average_cost":round(new_avg,8),
                "last_price":fill.price,
            }
            cash_delta=-total_cost
        else:
            old=self.positions.get(fill.symbol)
            if old is None or int(old["quantity"])<fill.quantity:
                raise ValueError("portfolio oversell")
            old_qty=int(old["quantity"])
            old_avg=float(old["average_cost"])
            proceeds=fill.gross_notional-fill.commission
            realized_delta=round((fill.price-old_avg)*fill.quantity-fill.commission,8)
            new_qty=old_qty-fill.quantity
            self.cash=round(self.cash+proceeds,8)
            self.realized_pnl=round(self.realized_pnl+realized_delta,8)
            if new_qty==0:
                del self.positions[fill.symbol]
            else:
                self.positions[fill.symbol]={
                    "quantity":new_qty,
                    "average_cost":old_avg,
                    "last_price":fill.price,
                }
            cash_delta=proceeds

        base={
            "sequence":self.sequence,
            "normalized_fill_id":fill.normalized_fill_id,
            "symbol":fill.symbol,
            "side":fill.side,
            "quantity":fill.quantity,
            "price":fill.price,
            "commission":fill.commission,
            "cash_delta":round(cash_delta,8),
            "realized_pnl_delta":round(realized_delta,8),
        }
        event=PortfolioFillEvent(
            sequence=self.sequence,
            normalized_fill_id=fill.normalized_fill_id,
            symbol=fill.symbol,
            side=fill.side,
            quantity=fill.quantity,
            price=fill.price,
            commission=fill.commission,
            cash_delta=round(cash_delta,8),
            realized_pnl_delta=round(realized_delta,8),
            event_sha256=digest_json(base),
        )
        self.events.append(event)
        self.applied_fill_ids.add(fill.normalized_fill_id)
        return event

    def mark_to_market(self, prices:dict[str,float])->dict:
        positions=[]
        market_value=0.0
        unrealized=0.0
        for symbol in sorted(self.positions):
            p=self.positions[symbol]
            price=float(prices.get(symbol,p["last_price"]))
            if price<=0:
                raise ValueError("invalid mark price")
            qty=int(p["quantity"])
            avg=float(p["average_cost"])
            mv=round(qty*price,8)
            upnl=round((price-avg)*qty,8)
            market_value=round(market_value+mv,8)
            unrealized=round(unrealized+upnl,8)
            positions.append({
                "symbol":symbol,"quantity":qty,"average_cost":avg,
                "last_price":price,"market_value":mv,"unrealized_pnl":upnl
            })
        equity=round(self.cash+market_value,8)
        return {
            "cash":self.cash,
            "market_value":market_value,
            "equity":equity,
            "realized_pnl":self.realized_pnl,
            "unrealized_pnl":unrealized,
            "total_pnl":round(self.realized_pnl+unrealized,8),
            "positions":positions,
            "event_count":len(self.events),
            "last_sequence":self.sequence,
        }

def replay_fill_events(starting_cash:float, events:list[PortfolioFillEvent])->dict:
    cash=float(starting_cash)
    realized=0.0
    last_sequence=0
    seen=set()
    for event in events:
        if event.sequence != last_sequence + 1:
            raise ValueError("event sequence gap")
        if event.normalized_fill_id in seen:
            raise ValueError("duplicate fill event")
        expected=digest_json({
            "sequence":event.sequence,
            "normalized_fill_id":event.normalized_fill_id,
            "symbol":event.symbol,
            "side":event.side,
            "quantity":event.quantity,
            "price":event.price,
            "commission":event.commission,
            "cash_delta":event.cash_delta,
            "realized_pnl_delta":event.realized_pnl_delta,
        })
        if expected != event.event_sha256:
            raise ValueError("event hash mismatch")
        cash=round(cash+event.cash_delta,8)
        realized=round(realized+event.realized_pnl_delta,8)
        seen.add(event.normalized_fill_id)
        last_sequence=event.sequence
    return {"cash":cash,"realized_pnl":realized,"last_sequence":last_sequence}

def build_fill_portfolio_bridge_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.60" or cert.get("status")!="PASS":
        errors.append("paper_broker_certificate")
    if cert.get("certification_scope")!="OFFLINE_FILL_PORTFOLIO_BRIDGE_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    bridge=config.get("fill_portfolio_bridge",{})
    for key in ("starting_cash","mark_prices","allow_real_broker_events"):
        if key not in bridge:
            errors.append(f"config_{key}")
    if bridge.get("allow_real_broker_events") is not False:
        errors.append("real_broker_events")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.61.fill_portfolio_foundation.1",
        "stage":"V78.61","status":status,
        "scope":"OFFLINE_FILL_ACCOUNTING_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "fill_portfolio_bridge":bridge,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_62_FILL_NORMALIZATION_PORTFOLIO_EVENT",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"fill_portfolio_bridge_foundation_v78_61.json",doc)
    ver={"stage":"V78.61","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"fill_portfolio_bridge_foundation_verification_v78_61.json",ver)
    return doc

def run_fill_normalization_portfolio_event(foundation_path:Path,fill_path:Path,output_dir:Path)->dict:
    foundation,fill_doc=map(load_json,(foundation_path,fill_path))
    errors=[]
    if foundation.get("stage")!="V78.61" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if fill_doc.get("stage")!="V78.58" or fill_doc.get("status")!="PASS":
        errors.append("fill_input")
    normalized=[]
    try:
        for raw in fill_doc.get("paper_fills",[]):
            normalized.append(normalize_fill(raw))
    except Exception as exc:
        errors.append(f"normalization_exception:{type(exc).__name__}")
    checks={
        "fill_count_preserved":len(normalized)==len(fill_doc.get("paper_fills",[])),
        "normalized_ids_unique":len({x.normalized_fill_id for x in normalized})==len(normalized),
        "source_fill_ids_unique":len({x.source_fill_id for x in normalized})==len(normalized),
        "normalized_hashes_unique":len({x.normalized_sha256 for x in normalized})==len(normalized),
        "gross_notional_valid":all(round(x.quantity*x.price,8)==x.gross_notional for x in normalized),
        "real_broker_events_disabled":foundation.get("fill_portfolio_bridge",{}).get("allow_real_broker_events") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("normalization_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.62.fill_normalization.1",
        "stage":"V78.62","status":status,
        "normalized_fills":[asdict(x) for x in normalized],
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_63_FILL_APPLICATION_RECONCILIATION",
    }
    doc["normalization_sha256"]=digest_json({k:v for k,v in doc.items() if k!="normalization_sha256"})
    write_json(output_dir/"fill_normalization_portfolio_event_v78_62.json",doc)
    ver={"stage":"V78.62","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "normalization_sha256":doc["normalization_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"fill_normalization_portfolio_event_verification_v78_62.json",ver)
    return doc

def run_fill_application_reconciliation(foundation_path:Path,normalization_path:Path,output_dir:Path)->dict:
    foundation,normalization=map(load_json,(foundation_path,normalization_path))
    errors=[]
    if foundation.get("stage")!="V78.61" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if normalization.get("stage")!="V78.62" or normalization.get("status")!="PASS":
        errors.append("normalization_input")
    runtime=FillPortfolioRuntime(float(foundation.get("fill_portfolio_bridge",{}).get("starting_cash",100000.0)))
    events=[]
    try:
        for raw in normalization.get("normalized_fills",[]):
            events.append(runtime.apply(NormalizedFill(**raw)))
        snapshot=runtime.mark_to_market(foundation.get("fill_portfolio_bridge",{}).get("mark_prices",{}))
        replay=replay_fill_events(runtime.starting_cash,events)
    except Exception as exc:
        snapshot={};replay={}
        errors.append(f"application_exception:{type(exc).__name__}")

    total_commission=round(sum(x.commission for x in events),8)
    checks={
        "event_count_matches_fills":len(events)==len(normalization.get("normalized_fills",[])),
        "event_sequences_contiguous":[x.sequence for x in events]==list(range(1,len(events)+1)),
        "event_hashes_unique":len({x.event_sha256 for x in events})==len(events),
        "replay_cash_matches":replay.get("cash")==snapshot.get("cash"),
        "replay_realized_matches":replay.get("realized_pnl")==snapshot.get("realized_pnl"),
        "round_trip_position_closed":snapshot.get("positions")==[],
        "round_trip_costs_reflected":snapshot.get("cash")==round(
            runtime.starting_cash
            - total_commission
            - sum(x.slippage_cost for x in [NormalizedFill(**r) for r in normalization.get("normalized_fills",[])])
        ,8),
        "equity_equals_cash_when_flat":snapshot.get("equity")==snapshot.get("cash"),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("reconciliation_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.63.fill_application_reconciliation.1",
        "stage":"V78.63","status":status,
        "portfolio_fill_events":[asdict(x) for x in events],
        "portfolio_snapshot":snapshot,
        "replay_state":replay,
        "total_commission":total_commission,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_64_FILL_PORTFOLIO_SAFETY_GATE",
    }
    doc["reconciliation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="reconciliation_sha256"})
    write_json(output_dir/"fill_application_reconciliation_v78_63.json",doc)
    ver={"stage":"V78.63","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "reconciliation_sha256":doc["reconciliation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"fill_application_reconciliation_verification_v78_63.json",ver)
    return doc

def run_fill_portfolio_safety_gate(foundation_path:Path,normalization_path:Path,
                                   reconciliation_path:Path,output_dir:Path)->dict:
    foundation,normalization,reconciliation=map(load_json,(foundation_path,normalization_path,reconciliation_path))
    errors=[]
    for expected,doc in (("V78.61",foundation),("V78.62",normalization),("V78.63",reconciliation)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    events=reconciliation.get("portfolio_fill_events",[])
    checks={
        "offline_fill_accounting_scope":foundation.get("scope")=="OFFLINE_FILL_ACCOUNTING_ONLY",
        "normalization_checks_passed":normalization.get("failed_checks")==[],
        "reconciliation_checks_passed":reconciliation.get("failed_checks")==[],
        "fill_event_ids_unique":len({x["normalized_fill_id"] for x in events})==len(events),
        "event_sequences_contiguous":[x["sequence"] for x in events]==list(range(1,len(events)+1)),
        "replay_consistent":reconciliation.get("checks",{}).get("replay_cash_matches") is True,
        "real_broker_events_disabled":foundation.get("fill_portfolio_bridge",{}).get("allow_real_broker_events") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,normalization,reconciliation)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,normalization,reconciliation)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,normalization,reconciliation)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("fill_portfolio_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.64.fill_portfolio_safety_gate.1",
        "stage":"V78.64","status":status,
        "gate_scope":"OFFLINE_AUDIT_RECONCILIATION_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_AUDIT_RECONCILIATION" if not errors else "BLOCK_AUDIT_RECONCILIATION",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_65_FILL_PORTFOLIO_BRIDGE_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"fill_portfolio_safety_gate_v78_64.json",doc)
    ver={"stage":"V78.64","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"fill_portfolio_safety_gate_verification_v78_64.json",ver)
    return doc

def issue_fill_portfolio_bridge_certificate(v61:Path,v62:Path,v63:Path,v64:Path,
                                            foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v61,v62,v63,v64)))
    foundation=load_json(foundation_path)
    expected=["V78.61","V78.62","V78.63","V78.64"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.65.fill_portfolio_certificate.1",
        "stage":"V78.65",
        "certificate_id":"FILL-PORTFOLIO-BRIDGE-V78.65",
        "status":status,
        "decision":"certified_for_offline_audit_reconciliation" if not errors else "fill_portfolio_bridge_rejected",
        "certification_scope":"OFFLINE_AUDIT_RECONCILIATION_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_66_AUDIT_RECONCILIATION_FOUNDATION" if not errors else "REPAIR_V78_65",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"fill_portfolio_bridge_certificate_v78_65.json",cert)
    ver={"stage":"V78.65","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"fill_portfolio_bridge_certificate_verification_v78_65.json",ver)
    return cert
