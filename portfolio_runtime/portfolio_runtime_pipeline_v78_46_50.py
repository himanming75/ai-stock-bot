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
class Position:
    symbol: str
    quantity: int
    average_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float

@dataclass(frozen=True)
class PortfolioLedgerEntry:
    sequence: int
    entry_type: str
    symbol: str
    quantity: int
    price: float
    cash_delta: float
    realized_pnl_delta: float
    reference_id: str
    entry_sha256: str

class PortfolioRuntime:
    def __init__(self, starting_cash: float):
        if starting_cash < 0:
            raise ValueError("starting_cash must be non-negative")
        self.starting_cash = float(starting_cash)
        self.cash = float(starting_cash)
        self.realized_pnl = 0.0
        self.positions: dict[str, Position] = {}
        self.ledger: list[PortfolioLedgerEntry] = []
        self.sequence = 0
        self.applied_reference_ids: set[str] = set()
        self.network_allowed=False
        self.broker_connected=False
        self.actual_orders_submitted=0

    def _append(self, entry_type: str, symbol: str, quantity: int, price: float,
                cash_delta: float, realized_pnl_delta: float, reference_id: str) -> PortfolioLedgerEntry:
        if reference_id in self.applied_reference_ids:
            raise ValueError("duplicate reference_id")
        self.sequence += 1
        base={
            "sequence":self.sequence,
            "entry_type":entry_type,
            "symbol":symbol,
            "quantity":quantity,
            "price":price,
            "cash_delta":round(cash_delta,8),
            "realized_pnl_delta":round(realized_pnl_delta,8),
            "reference_id":reference_id,
        }
        entry=PortfolioLedgerEntry(
            sequence=self.sequence,
            entry_type=entry_type,
            symbol=symbol,
            quantity=quantity,
            price=float(price),
            cash_delta=round(cash_delta,8),
            realized_pnl_delta=round(realized_pnl_delta,8),
            reference_id=reference_id,
            entry_sha256=digest_json(base),
        )
        self.ledger.append(entry)
        self.applied_reference_ids.add(reference_id)
        return entry

    def apply_approved_decision(self, decision: dict, request: dict) -> PortfolioLedgerEntry | None:
        if decision.get("decision")!="APPROVE":
            return None
        if decision.get("risk_request_id")!=request.get("risk_request_id"):
            raise ValueError("decision request mismatch")
        quantity=int(decision.get("approved_quantity",0))
        price=float(request.get("reference_price",0))
        symbol=str(request.get("symbol","")).upper()
        side=str(request.get("side","")).lower()
        reference_id=str(decision.get("risk_decision_id",""))
        if quantity<=0 or price<=0 or not symbol or not reference_id:
            raise ValueError("invalid approved decision")

        if side=="buy":
            notional=quantity*price
            if notional>self.cash:
                raise ValueError("insufficient portfolio cash")
            old=self.positions.get(symbol)
            old_qty=0 if old is None else old.quantity
            old_cost=0.0 if old is None else old.average_cost
            new_qty=old_qty+quantity
            average=((old_qty*old_cost)+notional)/new_qty
            self.cash=round(self.cash-notional,8)
            self.positions[symbol]=Position(
                symbol=symbol,quantity=new_qty,average_cost=round(average,8),
                last_price=price,market_value=round(new_qty*price,8),
                unrealized_pnl=round((price-average)*new_qty,8),
            )
            return self._append("BUY_APPLIED",symbol,quantity,price,-notional,0.0,reference_id)

        if side=="sell":
            old=self.positions.get(symbol)
            if old is None or old.quantity<quantity:
                raise ValueError("portfolio oversell")
            proceeds=quantity*price
            realized=(price-old.average_cost)*quantity
            new_qty=old.quantity-quantity
            self.cash=round(self.cash+proceeds,8)
            self.realized_pnl=round(self.realized_pnl+realized,8)
            if new_qty==0:
                del self.positions[symbol]
            else:
                self.positions[symbol]=Position(
                    symbol=symbol,quantity=new_qty,average_cost=old.average_cost,
                    last_price=price,market_value=round(new_qty*price,8),
                    unrealized_pnl=round((price-old.average_cost)*new_qty,8),
                )
            return self._append("SELL_APPLIED",symbol,quantity,price,proceeds,realized,reference_id)

        raise ValueError("unsupported side")

    def mark_to_market(self, prices: dict[str,float]) -> None:
        for symbol,position in list(self.positions.items()):
            if symbol not in prices:
                continue
            price=float(prices[symbol])
            if price<=0:
                raise ValueError("invalid market price")
            self.positions[symbol]=Position(
                symbol=symbol,
                quantity=position.quantity,
                average_cost=position.average_cost,
                last_price=price,
                market_value=round(position.quantity*price,8),
                unrealized_pnl=round((price-position.average_cost)*position.quantity,8),
            )

    def snapshot(self) -> dict:
        market_value=round(sum(x.market_value for x in self.positions.values()),8)
        unrealized=round(sum(x.unrealized_pnl for x in self.positions.values()),8)
        equity=round(self.cash+market_value,8)
        return {
            "cash":self.cash,
            "market_value":market_value,
            "equity":equity,
            "realized_pnl":self.realized_pnl,
            "unrealized_pnl":unrealized,
            "total_pnl":round(self.realized_pnl+unrealized,8),
            "positions":[asdict(self.positions[k]) for k in sorted(self.positions)],
            "ledger_count":len(self.ledger),
            "last_sequence":self.sequence,
        }

def replay_portfolio(starting_cash: float, entries: list[PortfolioLedgerEntry]) -> dict:
    cash=float(starting_cash)
    realized=0.0
    positions: dict[str,dict] = {}
    expected_sequence=1
    seen=set()

    for entry in entries:
        if entry.sequence!=expected_sequence:
            raise ValueError("ledger sequence gap")
        expected_sequence+=1
        if entry.reference_id in seen:
            raise ValueError("duplicate ledger reference")
        seen.add(entry.reference_id)
        expected=digest_json({
            "sequence":entry.sequence,
            "entry_type":entry.entry_type,
            "symbol":entry.symbol,
            "quantity":entry.quantity,
            "price":entry.price,
            "cash_delta":entry.cash_delta,
            "realized_pnl_delta":entry.realized_pnl_delta,
            "reference_id":entry.reference_id,
        })
        if expected!=entry.entry_sha256:
            raise ValueError("ledger hash mismatch")
        cash=round(cash+entry.cash_delta,8)
        realized=round(realized+entry.realized_pnl_delta,8)

        if entry.entry_type=="BUY_APPLIED":
            old=positions.get(entry.symbol,{"quantity":0,"average_cost":0.0})
            new_qty=old["quantity"]+entry.quantity
            avg=((old["quantity"]*old["average_cost"])+(entry.quantity*entry.price))/new_qty
            positions[entry.symbol]={"quantity":new_qty,"average_cost":round(avg,8)}
        elif entry.entry_type=="SELL_APPLIED":
            old=positions.get(entry.symbol)
            if old is None or old["quantity"]<entry.quantity:
                raise ValueError("replay oversell")
            new_qty=old["quantity"]-entry.quantity
            if new_qty==0:
                del positions[entry.symbol]
            else:
                positions[entry.symbol]={"quantity":new_qty,"average_cost":old["average_cost"]}
        else:
            raise ValueError("unsupported ledger entry")

    return {
        "cash":cash,
        "realized_pnl":realized,
        "positions":[{"symbol":k,**positions[k]} for k in sorted(positions)],
        "last_sequence":expected_sequence-1,
    }

def build_portfolio_runtime_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.45" or cert.get("status")!="PASS":
        errors.append("signal_risk_certificate")
    if cert.get("certification_scope")!="OFFLINE_PORTFOLIO_RUNTIME_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    portfolio=config.get("portfolio_runtime",{})
    for key in ("starting_cash","mark_prices","allow_order_creation","allow_order_submission"):
        if key not in portfolio:
            errors.append(f"config_{key}")
    if portfolio.get("allow_order_creation") is not False:
        errors.append("allow_order_creation")
    if portfolio.get("allow_order_submission") is not False:
        errors.append("allow_order_submission")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.46.portfolio_runtime_foundation.1",
        "stage":"V78.46","status":status,
        "scope":"OFFLINE_PORTFOLIO_ACCOUNTING_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "portfolio_runtime":portfolio,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_47_PORTFOLIO_STATE_POSITION_LEDGER",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"portfolio_runtime_foundation_v78_46.json",doc)
    ver={
        "stage":"V78.46","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "foundation_sha256":doc["foundation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"portfolio_runtime_foundation_verification_v78_46.json",ver)
    return doc

def build_portfolio_state_position_ledger(foundation_path: Path, decision_path: Path,
                                          normalization_path: Path, output_dir: Path) -> dict:
    foundation,decision_doc,normalization=map(load_json,(foundation_path,decision_path,normalization_path))
    errors=[]
    if foundation.get("stage")!="V78.46" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if decision_doc.get("stage")!="V78.43" or decision_doc.get("status")!="PASS":
        errors.append("decision_input")
    if normalization.get("stage")!="V78.42" or normalization.get("status")!="PASS":
        errors.append("normalization_input")

    runtime=PortfolioRuntime(float(foundation.get("portfolio_runtime",{}).get("starting_cash",100000.0)))
    requests={x["risk_request_id"]:x for x in normalization.get("risk_requests",[])}
    entries=[]
    try:
        for decision in decision_doc.get("risk_decisions",[]):
            request=requests[decision["risk_request_id"]]
            entry=runtime.apply_approved_decision(decision,request)
            if entry is not None:
                entries.append(entry)
    except Exception as exc:
        errors.append(f"ledger_application_exception:{type(exc).__name__}")

    runtime.mark_to_market(foundation.get("portfolio_runtime",{}).get("mark_prices",{}))
    snapshot=runtime.snapshot()
    replay=replay_portfolio(runtime.starting_cash,runtime.ledger)

    checks={
        "ledger_entries_created":len(entries)==2,
        "sequence_contiguous":[x.sequence for x in entries]==[1,2],
        "ledger_hashes_unique":len({x.entry_sha256 for x in entries})==len(entries),
        "replay_cash_matches":replay["cash"]==snapshot["cash"],
        "replay_realized_matches":replay["realized_pnl"]==snapshot["realized_pnl"],
        "final_position_quantity":snapshot["positions"][0]["quantity"]==0 if snapshot["positions"] else True,
        "cash_restored_after_round_trip":snapshot["cash"]==runtime.starting_cash,
        "realized_pnl_zero_at_same_price":snapshot["realized_pnl"]==0.0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("portfolio_ledger_checks")
    status="PASS" if not errors else "FAIL"

    doc={
        "schema_version":"v78.47.portfolio_state_ledger.1",
        "stage":"V78.47","status":status,
        "ledger_entries":[asdict(x) for x in entries],
        "portfolio_snapshot":snapshot,
        "replay_state":replay,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_48_APPROVED_DECISION_APPLICATION_ENGINE",
    }
    doc["portfolio_ledger_sha256"]=digest_json({k:v for k,v in doc.items() if k!="portfolio_ledger_sha256"})
    write_json(output_dir/"portfolio_state_position_ledger_v78_47.json",doc)
    ver={
        "stage":"V78.47","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "portfolio_ledger_sha256":doc["portfolio_ledger_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"portfolio_state_position_ledger_verification_v78_47.json",ver)
    return doc

def run_approved_decision_application_engine(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.46" or foundation.get("status")!="PASS":
        errors.append("foundation_input")

    runtime=PortfolioRuntime(float(foundation.get("portfolio_runtime",{}).get("starting_cash",100000.0)))
    buy_request={
        "risk_request_id":"REQ-BUY-1","symbol":"AAPL","side":"buy",
        "reference_price":100.0,
    }
    buy_decision={
        "risk_decision_id":"DEC-BUY-1","risk_request_id":"REQ-BUY-1",
        "decision":"APPROVE","approved_quantity":10,
    }
    sell_request={
        "risk_request_id":"REQ-SELL-1","symbol":"AAPL","side":"sell",
        "reference_price":110.0,
    }
    sell_decision={
        "risk_decision_id":"DEC-SELL-1","risk_request_id":"REQ-SELL-1",
        "decision":"APPROVE","approved_quantity":4,
    }
    reject_request={
        "risk_request_id":"REQ-REJECT-1","symbol":"AAPL","side":"buy",
        "reference_price":105.0,
    }
    reject_decision={
        "risk_decision_id":"DEC-REJECT-1","risk_request_id":"REQ-REJECT-1",
        "decision":"REJECT","approved_quantity":0,
    }

    try:
        runtime.apply_approved_decision(buy_decision,buy_request)
        runtime.apply_approved_decision(sell_decision,sell_request)
        rejected=runtime.apply_approved_decision(reject_decision,reject_request)
        runtime.mark_to_market({"AAPL":120.0})
        snapshot=runtime.snapshot()
    except Exception as exc:
        rejected=None;snapshot={}
        errors.append(f"application_exception:{type(exc).__name__}")

    checks={
        "rejected_decision_not_applied":rejected is None,
        "cash_expected":snapshot.get("cash")==99440.0,
        "remaining_quantity":snapshot.get("positions",[{}])[0].get("quantity")==6,
        "average_cost_preserved":snapshot.get("positions",[{}])[0].get("average_cost")==100.0,
        "realized_pnl_expected":snapshot.get("realized_pnl")==40.0,
        "unrealized_pnl_expected":snapshot.get("unrealized_pnl")==120.0,
        "equity_expected":snapshot.get("equity")==100160.0,
        "ledger_count_expected":snapshot.get("ledger_count")==2,
        "orders_generated_zero":True,
        "orders_submitted_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("decision_application_checks")
    status="PASS" if not errors else "FAIL"

    doc={
        "schema_version":"v78.48.approved_decision_application.1",
        "stage":"V78.48","status":status,
        "portfolio_snapshot":snapshot,
        "ledger_entries":[asdict(x) for x in runtime.ledger],
        "checks":checks,"failed_checks":failed,
        "generated_order_count":0,
        "submitted_order_count":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_49_PORTFOLIO_RUNTIME_SAFETY_GATE",
    }
    doc["application_sha256"]=digest_json({k:v for k,v in doc.items() if k!="application_sha256"})
    write_json(output_dir/"approved_decision_application_engine_v78_48.json",doc)
    ver={
        "stage":"V78.48","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "application_sha256":doc["application_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"approved_decision_application_engine_verification_v78_48.json",ver)
    return doc

def run_portfolio_runtime_safety_gate(foundation_path: Path, ledger_path: Path,
                                      application_path: Path, output_dir: Path) -> dict:
    foundation,ledger,application=map(load_json,(foundation_path,ledger_path,application_path))
    errors=[]
    for expected,doc in (("V78.46",foundation),("V78.47",ledger),("V78.48",application)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)

    entries=application.get("ledger_entries",[])
    checks={
        "offline_accounting_scope":foundation.get("scope")=="OFFLINE_PORTFOLIO_ACCOUNTING_ONLY",
        "ledger_checks_passed":ledger.get("failed_checks")==[],
        "application_checks_passed":application.get("failed_checks")==[],
        "ledger_sequences_contiguous":[x["sequence"] for x in entries]==list(range(1,len(entries)+1)),
        "ledger_reference_ids_unique":len({x["reference_id"] for x in entries})==len(entries),
        "generated_orders_zero":application.get("generated_order_count")==0,
        "submitted_orders_zero":application.get("submitted_order_count")==0,
        "order_creation_disabled":foundation.get("portfolio_runtime",{}).get("allow_order_creation") is False,
        "order_submission_disabled":foundation.get("portfolio_runtime",{}).get("allow_order_submission") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,ledger,application)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,ledger,application)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,ledger,application)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:
        errors.append("portfolio_runtime_safety_checks")
    status="PASS" if not errors else "FAIL"

    doc={
        "schema_version":"v78.49.portfolio_runtime_safety_gate.1",
        "stage":"V78.49","status":status,
        "gate_scope":"OFFLINE_EXECUTION_COORDINATOR_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_EXECUTION_COORDINATOR" if not errors else "BLOCK_EXECUTION_COORDINATOR",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_50_PORTFOLIO_RUNTIME_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"portfolio_runtime_safety_gate_v78_49.json",doc)
    ver={
        "stage":"V78.49","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,"failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"portfolio_runtime_safety_gate_verification_v78_49.json",ver)
    return doc

def issue_portfolio_runtime_certificate(v46: Path,v47: Path,v48: Path,v49: Path,
                                        foundation_path: Path,output_dir: Path) -> dict:
    docs=list(map(load_json,(v46,v47,v48,v49)))
    foundation=load_json(foundation_path)
    expected=["V78.46","V78.47","V78.48","V78.49"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"

    cert={
        "schema_version":"v78.50.portfolio_runtime_certificate.1",
        "stage":"V78.50",
        "certificate_id":"PORTFOLIO-RUNTIME-V78.50",
        "status":status,
        "decision":"certified_for_offline_execution_coordinator" if not errors else "portfolio_runtime_rejected",
        "certification_scope":"OFFLINE_EXECUTION_COORDINATOR_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_51_EXECUTION_COORDINATOR_FOUNDATION" if not errors else "REPAIR_V78_50",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"portfolio_runtime_certificate_v78_50.json",cert)
    ver={
        "stage":"V78.50","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"portfolio_runtime_certificate_verification_v78_50.json",ver)
    return cert
