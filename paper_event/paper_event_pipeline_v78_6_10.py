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
class PaperEvent:
    event_id: str
    sequence: int
    event_type: str
    aggregate_id: str
    payload: dict
    previous_event_sha256: str
    event_sha256: str

class PaperEventFactory:
    def __init__(self, stream_id: str):
        if not stream_id:
            raise ValueError("stream_id required")
        self.stream_id = stream_id

    def create(self, sequence: int, event_type: str, aggregate_id: str,
               payload: dict, previous_event_sha256: str) -> PaperEvent:
        if sequence <= 0:
            raise ValueError("sequence must be positive")
        if not event_type:
            raise ValueError("event_type required")
        if not aggregate_id:
            raise ValueError("aggregate_id required")
        base = {
            "stream_id":self.stream_id,
            "sequence":sequence,
            "event_type":event_type,
            "aggregate_id":aggregate_id,
            "payload":payload,
            "previous_event_sha256":previous_event_sha256,
        }
        event_sha = digest_json(base)
        event_id = f"{self.stream_id}-EVT-{sequence:08d}-{event_sha[:12]}"
        return PaperEvent(
            event_id=event_id,
            sequence=sequence,
            event_type=event_type,
            aggregate_id=aggregate_id,
            payload=dict(payload),
            previous_event_sha256=previous_event_sha256,
            event_sha256=event_sha,
        )

class AppendOnlyEventLedger:
    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self._events: list[PaperEvent] = []
        self._event_ids: set[str] = set()

    def append(self, event: PaperEvent) -> None:
        expected_sequence = len(self._events) + 1
        expected_previous = self._events[-1].event_sha256 if self._events else "GENESIS"
        if event.sequence != expected_sequence:
            raise ValueError("sequence gap or reorder")
        if event.previous_event_sha256 != expected_previous:
            raise ValueError("previous hash mismatch")
        if event.event_id in self._event_ids:
            raise ValueError("duplicate event")
        expected = digest_json({
            "stream_id":self.stream_id,
            "sequence":event.sequence,
            "event_type":event.event_type,
            "aggregate_id":event.aggregate_id,
            "payload":event.payload,
            "previous_event_sha256":event.previous_event_sha256,
        })
        if event.event_sha256 != expected:
            raise ValueError("event hash mismatch")
        self._events.append(event)
        self._event_ids.add(event.event_id)

    def events(self) -> list[PaperEvent]:
        return list(self._events)

    def ledger_sha256(self) -> str:
        return digest_json([asdict(x) for x in self._events])

    def verify(self) -> dict:
        previous = "GENESIS"
        errors = []
        seen = set()
        for index,event in enumerate(self._events,1):
            if event.sequence != index:
                errors.append(f"sequence:{index}")
            if event.previous_event_sha256 != previous:
                errors.append(f"previous_hash:{index}")
            if event.event_id in seen:
                errors.append(f"duplicate:{event.event_id}")
            expected = digest_json({
                "stream_id":self.stream_id,
                "sequence":event.sequence,
                "event_type":event.event_type,
                "aggregate_id":event.aggregate_id,
                "payload":event.payload,
                "previous_event_sha256":event.previous_event_sha256,
            })
            if event.event_sha256 != expected:
                errors.append(f"event_hash:{index}")
            seen.add(event.event_id)
            previous = event.event_sha256
        return {
            "verified":not errors,
            "error_count":len(errors),
            "errors":errors,
            "event_count":len(self._events),
            "ledger_sha256":self.ledger_sha256(),
        }

def replay_events(events: list[PaperEvent], starting_cash: float = 100000.0) -> dict:
    cash = float(starting_cash)
    positions: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    applied_event_ids = set()
    expected_sequence = 1

    for event in events:
        if event.event_id in applied_event_ids:
            raise ValueError("duplicate event during replay")
        if event.sequence != expected_sequence:
            raise ValueError("sequence gap during replay")
        expected_sequence += 1
        applied_event_ids.add(event.event_id)
        p = event.payload

        if event.event_type == "ORDER_CREATED":
            orders[event.aggregate_id] = {
                "order_id":event.aggregate_id,
                "symbol":p["symbol"],
                "side":p["side"],
                "quantity":int(p["quantity"]),
                "status":"CREATED",
            }
        elif event.event_type == "ORDER_ACCEPTED":
            if event.aggregate_id not in orders:
                raise ValueError("accepted order missing")
            orders[event.aggregate_id]["status"] = "ACCEPTED"
        elif event.event_type == "ORDER_FILLED":
            if event.aggregate_id not in orders:
                raise ValueError("filled order missing")
            order = orders[event.aggregate_id]
            qty = int(p["quantity"])
            price = float(p["price"])
            notional = qty * price
            symbol = order["symbol"]
            if order["side"] == "buy":
                if notional > cash:
                    raise ValueError("insufficient replay cash")
                cash -= notional
                old = positions.get(symbol, {"quantity":0,"average_price":0.0})
                old_qty = int(old["quantity"])
                new_qty = old_qty + qty
                avg = ((old_qty*float(old["average_price"])) + notional) / new_qty
                positions[symbol] = {"symbol":symbol,"quantity":new_qty,"average_price":round(avg,8)}
            else:
                old = positions.get(symbol)
                if old is None or int(old["quantity"]) < qty:
                    raise ValueError("replay oversell")
                new_qty = int(old["quantity"]) - qty
                cash += notional
                if new_qty == 0:
                    del positions[symbol]
                else:
                    positions[symbol] = {
                        "symbol":symbol,
                        "quantity":new_qty,
                        "average_price":old["average_price"],
                    }
            order["status"] = "FILLED"
            order["fill_price"] = price
        elif event.event_type == "ORDER_CANCELED":
            if event.aggregate_id not in orders:
                raise ValueError("canceled order missing")
            if orders[event.aggregate_id]["status"] == "FILLED":
                raise ValueError("cannot cancel filled order")
            orders[event.aggregate_id]["status"] = "CANCELED"
        else:
            raise ValueError("unsupported event type")

    return {
        "cash":round(cash,8),
        "positions":[positions[k] for k in sorted(positions)],
        "orders":[orders[k] for k in sorted(orders)],
        "applied_event_count":len(applied_event_ids),
        "last_sequence":expected_sequence-1,
    }

def build_paper_event_engine(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors = []
    if cert.get("stage")!="V78.5" or cert.get("status")!="PASS":
        errors.append("paper_broker_certificate")
    if cert.get("certification_scope")!="OFFLINE_PAPER_BROKER_RUNTIME_ONLY":
        errors.append("certificate_scope")
    event_cfg = config.get("paper_event",{})
    for key in ("stream_id","starting_cash","allowed_event_types","hash_algorithm"):
        if key not in event_cfg:
            errors.append(f"config_{key}")
    if event_cfg.get("hash_algorithm")!="sha256":
        errors.append("hash_algorithm")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.6.paper_event_engine.1",
        "stage":"V78.6","status":status,
        "scope":"OFFLINE_EVENT_SOURCING_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "paper_event":event_cfg,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_7_ORDER_FILL_EVENT_LEDGER",
    }
    doc["event_engine_sha256"] = digest_json({k:v for k,v in doc.items() if k!="event_engine_sha256"})
    write_json(output_dir/"paper_event_engine_v78_6.json",doc)
    ver = {
        "stage":"V78.6","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "event_engine_sha256":doc["event_engine_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_event_engine_verification_v78_6.json",ver)
    return doc

def build_order_fill_event_ledger(engine_path: Path, output_dir: Path) -> dict:
    engine = load_json(engine_path)
    errors = []
    if engine.get("stage")!="V78.6" or engine.get("status")!="PASS":
        errors.append("engine_input")

    cfg = engine.get("paper_event",{})
    factory = PaperEventFactory(cfg.get("stream_id","PAPER-V78"))
    ledger = AppendOnlyEventLedger(cfg.get("stream_id","PAPER-V78"))
    specs = [
        ("ORDER_CREATED","ORD-0001",{"symbol":"AAPL","side":"buy","quantity":10}),
        ("ORDER_ACCEPTED","ORD-0001",{}),
        ("ORDER_FILLED","ORD-0001",{"quantity":10,"price":100.0}),
        ("ORDER_CREATED","ORD-0002",{"symbol":"AAPL","side":"sell","quantity":4}),
        ("ORDER_ACCEPTED","ORD-0002",{}),
        ("ORDER_FILLED","ORD-0002",{"quantity":4,"price":110.0}),
        ("ORDER_CREATED","ORD-0003",{"symbol":"MSFT","side":"buy","quantity":1}),
        ("ORDER_CANCELED","ORD-0003",{}),
    ]
    previous = "GENESIS"
    try:
        for sequence,(event_type,aggregate_id,payload) in enumerate(specs,1):
            event = factory.create(sequence,event_type,aggregate_id,payload,previous)
            ledger.append(event)
            previous = event.event_sha256
    except Exception as exc:
        errors.append(f"ledger_exception:{type(exc).__name__}")

    verification = ledger.verify()
    if not verification["verified"]:
        errors.append("ledger_verification")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.7.order_fill_event_ledger.1",
        "stage":"V78.7","status":status,
        "stream_id":ledger.stream_id,
        "events":[asdict(x) for x in ledger.events()],
        "ledger_verification":verification,
        "append_only":True,
        "hash_chain_enabled":True,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_8_EVENT_REPLAY_RECOVERY",
    }
    doc["event_ledger_sha256"] = digest_json({k:v for k,v in doc.items() if k!="event_ledger_sha256"})
    write_json(output_dir/"order_fill_event_ledger_v78_7.json",doc)
    ver = {
        "stage":"V78.7","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "event_count":len(doc["events"]),
        "event_ledger_sha256":doc["event_ledger_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"order_fill_event_ledger_verification_v78_7.json",ver)
    return doc

def run_event_replay_recovery(engine_path: Path, ledger_path: Path, output_dir: Path) -> dict:
    engine, ledger_doc = map(load_json,(engine_path,ledger_path))
    errors = []
    if engine.get("stage")!="V78.6" or engine.get("status")!="PASS":
        errors.append("engine_input")
    if ledger_doc.get("stage")!="V78.7" or ledger_doc.get("status")!="PASS":
        errors.append("ledger_input")
    events = [PaperEvent(**x) for x in ledger_doc.get("events",[])]
    try:
        state1 = replay_events(events,float(engine.get("paper_event",{}).get("starting_cash",100000.0)))
        state2 = replay_events(events,float(engine.get("paper_event",{}).get("starting_cash",100000.0)))
    except Exception as exc:
        state1 = {};state2 = {}
        errors.append(f"replay_exception:{type(exc).__name__}")

    checks = {
        "deterministic_replay":state1==state2,
        "cash_expected":state1.get("cash")==99440.0,
        "position_expected":state1.get("positions")==[
            {"symbol":"AAPL","quantity":6,"average_price":100.0}
        ],
        "order_count_expected":len(state1.get("orders",[]))==3,
        "event_count_expected":state1.get("applied_event_count")==8,
        "last_sequence_expected":state1.get("last_sequence")==8,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("replay_recovery_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.8.event_replay_recovery.1",
        "stage":"V78.8","status":status,
        "recovered_state":state1,
        "replay_state_sha256":digest_json(state1),
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_9_PAPER_EVENT_SAFETY_GATE",
    }
    doc["recovery_sha256"] = digest_json({k:v for k,v in doc.items() if k!="recovery_sha256"})
    write_json(output_dir/"event_replay_recovery_v78_8.json",doc)
    ver = {
        "stage":"V78.8","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "recovery_sha256":doc["recovery_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"event_replay_recovery_verification_v78_8.json",ver)
    return doc

def run_paper_event_safety_gate(engine_path: Path, ledger_path: Path, recovery_path: Path, output_dir: Path) -> dict:
    engine, ledger, recovery = map(load_json,(engine_path,ledger_path,recovery_path))
    errors = []
    for expected,doc in (("V78.6",engine),("V78.7",ledger),("V78.8",recovery)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    lv = ledger.get("ledger_verification",{})
    checks = {
        "ledger_append_only":ledger.get("append_only") is True,
        "hash_chain_enabled":ledger.get("hash_chain_enabled") is True,
        "ledger_verified":lv.get("verified") is True,
        "ledger_error_count_zero":lv.get("error_count")==0,
        "event_ids_unique":len({x["event_id"] for x in ledger.get("events",[])})==len(ledger.get("events",[])),
        "sequences_contiguous":[x["sequence"] for x in ledger.get("events",[])]==list(range(1,len(ledger.get("events",[]))+1)),
        "replay_deterministic":recovery.get("checks",{}).get("deterministic_replay") is True,
        "recovery_checks_passed":recovery.get("failed_checks")==[],
        "network_disabled":all(x.get("network_allowed") is False for x in (engine,ledger,recovery)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (engine,ledger,recovery)),
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("paper_event_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.9.paper_event_safety_gate.1",
        "stage":"V78.9","status":status,
        "gate_scope":"OFFLINE_EVENT_BUS_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_EVENT_BUS_FOUNDATION" if not errors else "BLOCK_EVENT_BUS_FOUNDATION",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_10_PAPER_EVENT_CERTIFICATE",
    }
    doc["safety_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"paper_event_safety_gate_v78_9.json",doc)
    ver = {
        "stage":"V78.9","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_event_safety_gate_verification_v78_9.json",ver)
    return doc

def issue_paper_event_certificate(v6: Path,v7: Path,v8: Path,v9: Path,engine_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v6,v7,v8,v9)))
    engine = load_json(engine_path)
    expected = ["V78.6","V78.7","V78.8","V78.9"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v78.10.paper_event_certificate.1",
        "stage":"V78.10",
        "certificate_id":"PAPER-EVENT-ENGINE-V78.10",
        "status":status,
        "decision":"certified_for_offline_event_bus_foundation" if not errors else "paper_event_rejected",
        "certification_scope":"OFFLINE_EVENT_BUS_FOUNDATION_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":engine.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_11_EVENT_BUS_FOUNDATION" if not errors else "REPAIR_V78_10",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"paper_event_certificate_v78_10.json",cert)
    ver = {
        "stage":"V78.10","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_event_certificate_verification_v78_10.json",ver)
    return cert
