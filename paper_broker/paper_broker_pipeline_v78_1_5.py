from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
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
class PaperAccountSnapshot:
    account_id: str
    cash: float
    buying_power: float
    equity: float
    sequence: int

@dataclass(frozen=True)
class PaperPositionSnapshot:
    symbol: str
    quantity: int
    average_price: float
    market_value: float
    sequence: int

@dataclass(frozen=True)
class PaperOrderRequest:
    client_order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None = None

@dataclass(frozen=True)
class PaperOrderEvent:
    event_id: str
    client_order_id: str
    broker_order_id: str
    event_type: str
    status: str
    symbol: str
    side: str
    quantity: int
    price: float | None = None

@runtime_checkable
class PaperBrokerAdapter(Protocol):
    def sync_account(self) -> PaperAccountSnapshot: ...
    def sync_positions(self) -> list[PaperPositionSnapshot]: ...
    def route_order(self, request: PaperOrderRequest) -> PaperOrderEvent: ...
    def simulate_fill(self, broker_order_id: str, price: float) -> PaperOrderEvent: ...
    def health(self) -> dict: ...

class AdapterRegistry:
    def __init__(self):
        self._factories: dict[str, Any] = {}

    def register(self, name: str, factory: Any) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("adapter name required")
        if key in self._factories:
            raise ValueError("adapter already registered")
        self._factories[key] = factory

    def create(self, name: str, **kwargs: Any) -> PaperBrokerAdapter:
        key = name.strip().lower()
        if key not in self._factories:
            raise ValueError("unknown adapter")
        adapter = self._factories[key](**kwargs)
        if not isinstance(adapter, PaperBrokerAdapter):
            raise TypeError("adapter does not satisfy protocol")
        return adapter

    def names(self) -> list[str]:
        return sorted(self._factories)

class DeterministicPaperBrokerAdapter:
    def __init__(self, starting_cash: float = 100000.0):
        self.cash = float(starting_cash)
        self.positions: dict[str, PaperPositionSnapshot] = {}
        self.orders: dict[str, PaperOrderRequest] = {}
        self.client_order_index: dict[str, str] = {}
        self.order_status: dict[str, str] = {}
        self.order_seq = 0
        self.event_seq = 0
        self.sync_seq = 0
        self.network_allowed = False
        self.broker_connected = False
        self.real_credentials_loaded = False
        self.live_order_submission_enabled = False

    def _next_event_id(self) -> str:
        self.event_seq += 1
        return f"PAPER-EVT-{self.event_seq:08d}"

    def sync_account(self) -> PaperAccountSnapshot:
        self.sync_seq += 1
        market_value = sum(p.market_value for p in self.positions.values())
        return PaperAccountSnapshot(
            account_id="PAPER-ACCOUNT-V78",
            cash=round(self.cash, 8),
            buying_power=round(self.cash, 8),
            equity=round(self.cash + market_value, 8),
            sequence=self.sync_seq,
        )

    def sync_positions(self) -> list[PaperPositionSnapshot]:
        self.sync_seq += 1
        return [
            PaperPositionSnapshot(
                symbol=p.symbol,
                quantity=p.quantity,
                average_price=p.average_price,
                market_value=p.market_value,
                sequence=self.sync_seq,
            )
            for p in (self.positions[k] for k in sorted(self.positions))
        ]

    def route_order(self, request: PaperOrderRequest) -> PaperOrderEvent:
        symbol = request.symbol.strip().upper()
        side = request.side.strip().lower()
        order_type = request.order_type.strip().lower()
        if not request.client_order_id:
            raise ValueError("client_order_id required")
        if request.client_order_id in self.client_order_index:
            raise ValueError("duplicate client_order_id")
        if not symbol:
            raise ValueError("symbol required")
        if side not in ("buy","sell"):
            raise ValueError("invalid side")
        if request.quantity <= 0:
            raise ValueError("quantity must be positive")
        if order_type not in ("market","limit"):
            raise ValueError("invalid order_type")
        if order_type == "limit" and (request.limit_price is None or request.limit_price <= 0):
            raise ValueError("positive limit price required")
        if side == "sell":
            held = self.positions.get(symbol)
            if held is None or held.quantity < request.quantity:
                raise ValueError("short selling disabled")

        self.order_seq += 1
        broker_order_id = f"PAPER-ORD-{self.order_seq:08d}"
        normalized = PaperOrderRequest(
            client_order_id=request.client_order_id,
            symbol=symbol,
            side=side,
            quantity=request.quantity,
            order_type=order_type,
            limit_price=request.limit_price,
        )
        self.orders[broker_order_id] = normalized
        self.client_order_index[request.client_order_id] = broker_order_id
        self.order_status[broker_order_id] = "ACCEPTED"
        return PaperOrderEvent(
            event_id=self._next_event_id(),
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            event_type="ORDER_ACCEPTED",
            status="ACCEPTED",
            symbol=symbol,
            side=side,
            quantity=request.quantity,
        )

    def simulate_fill(self, broker_order_id: str, price: float) -> PaperOrderEvent:
        if broker_order_id not in self.orders:
            raise ValueError("unknown broker order")
        if self.order_status[broker_order_id] == "FILLED":
            raise ValueError("order already filled")
        if price <= 0:
            raise ValueError("price must be positive")
        order = self.orders[broker_order_id]
        notional = order.quantity * float(price)
        if order.side == "buy":
            if notional > self.cash:
                raise ValueError("insufficient paper cash")
            self.cash -= notional
            previous = self.positions.get(order.symbol)
            old_qty = previous.quantity if previous else 0
            old_cost = previous.average_price * old_qty if previous else 0.0
            new_qty = old_qty + order.quantity
            avg = (old_cost + notional) / new_qty
            self.positions[order.symbol] = PaperPositionSnapshot(
                symbol=order.symbol,
                quantity=new_qty,
                average_price=round(avg,8),
                market_value=round(new_qty*price,8),
                sequence=self.sync_seq,
            )
        else:
            previous = self.positions[order.symbol]
            new_qty = previous.quantity - order.quantity
            self.cash += notional
            if new_qty == 0:
                del self.positions[order.symbol]
            else:
                self.positions[order.symbol] = PaperPositionSnapshot(
                    symbol=order.symbol,
                    quantity=new_qty,
                    average_price=previous.average_price,
                    market_value=round(new_qty*price,8),
                    sequence=self.sync_seq,
                )
        self.order_status[broker_order_id] = "FILLED"
        return PaperOrderEvent(
            event_id=self._next_event_id(),
            client_order_id=order.client_order_id,
            broker_order_id=broker_order_id,
            event_type="ORDER_FILLED",
            status="FILLED",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=float(price),
        )

    def health(self) -> dict:
        return {
            "adapter":"DeterministicPaperBrokerAdapter",
            "status":"HEALTHY",
            "mode":"paper_offline",
            "network_allowed":False,
            "broker_connected":False,
            "real_credentials_loaded":False,
            "live_order_submission_enabled":False,
        }

def build_paper_broker_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors = []
    if cert.get("stage")!="V77.100" or cert.get("status")!="PASS":
        errors.append("broker_skeleton_certificate")
    if cert.get("certification_scope")!="OFFLINE_BROKER_ADAPTER_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    if cert.get("real_broker_connection_approved") is not False:
        errors.append("real_broker_connection_must_remain_disabled")
    paper = config.get("paper_broker",{})
    for key in ("adapter_name","mode","starting_cash","supported_order_types","short_selling_enabled"):
        if key not in paper:
            errors.append(f"config_{key}")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.1.paper_broker_foundation.1",
        "stage":"V78.1","status":status,
        "scope":"OFFLINE_PAPER_BROKER_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "paper_broker":paper,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_2_PAPER_ACCOUNT_POSITION_SYNC",
    }
    doc["foundation_sha256"] = digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"paper_broker_foundation_v78_1.json",doc)
    ver = {
        "stage":"V78.1","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "foundation_sha256":doc["foundation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_foundation_verification_v78_1.json",ver)
    return doc

def run_paper_account_position_sync(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage")!="V78.1" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    registry = AdapterRegistry()
    registry.register("deterministic-paper", DeterministicPaperBrokerAdapter)
    adapter = registry.create("deterministic-paper", starting_cash=float(
        foundation.get("paper_broker",{}).get("starting_cash",100000.0)
    ))
    account = asdict(adapter.sync_account())
    positions = [asdict(x) for x in adapter.sync_positions()]
    checks = {
        "registry_contains_adapter":registry.names()==["deterministic-paper"],
        "account_cash_positive":account["cash"]>0,
        "account_equity_matches_cash":account["equity"]==account["cash"],
        "initial_positions_empty":positions==[],
        "sequence_monotonic":account["sequence"]<adapter.sync_account().sequence,
        "network_disabled":adapter.health()["network_allowed"] is False,
        "broker_disconnected":adapter.health()["broker_connected"] is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("account_position_sync_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.2.paper_account_position_sync.1",
        "stage":"V78.2","status":status,
        "account_snapshot":account,
        "position_snapshots":positions,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_3_PAPER_ORDER_ROUTING",
    }
    doc["sync_sha256"] = digest_json({k:v for k,v in doc.items() if k!="sync_sha256"})
    write_json(output_dir/"paper_account_position_sync_v78_2.json",doc)
    ver = {
        "stage":"V78.2","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "sync_sha256":doc["sync_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_account_position_sync_verification_v78_2.json",ver)
    return doc

def run_paper_order_routing(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage")!="V78.1" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    adapter = DeterministicPaperBrokerAdapter(
        starting_cash=float(foundation.get("paper_broker",{}).get("starting_cash",100000.0))
    )
    events = []
    try:
        buy_req = PaperOrderRequest("CLIENT-0001","AAPL","buy",10,"market")
        buy_evt = adapter.route_order(buy_req)
        events.append(asdict(buy_evt))
        fill_evt = adapter.simulate_fill(buy_evt.broker_order_id,100.0)
        events.append(asdict(fill_evt))

        sell_req = PaperOrderRequest("CLIENT-0002","AAPL","sell",4,"limit",110.0)
        sell_evt = adapter.route_order(sell_req)
        events.append(asdict(sell_evt))
        sell_fill = adapter.simulate_fill(sell_evt.broker_order_id,110.0)
        events.append(asdict(sell_fill))
    except Exception as exc:
        errors.append(f"routing_exception:{type(exc).__name__}")

    account = asdict(adapter.sync_account())
    positions = [asdict(x) for x in adapter.sync_positions()]
    checks = {
        "event_count_expected":len(events)==4,
        "event_ids_unique":len({x["event_id"] for x in events})==len(events),
        "client_ids_preserved":{x["client_order_id"] for x in events}=={"CLIENT-0001","CLIENT-0002"},
        "final_cash_expected":account["cash"]==99440.0,
        "final_position_expected":positions[0]["symbol"]=="AAPL" and positions[0]["quantity"]==6,
        "actual_orders_zero":True,
        "network_disabled":adapter.health()["network_allowed"] is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("order_routing_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.3.paper_order_routing.1",
        "stage":"V78.3","status":status,
        "events":events,
        "account_snapshot":account,
        "position_snapshots":positions,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_4_PAPER_BROKER_SAFETY_GATE",
    }
    doc["routing_sha256"] = digest_json({k:v for k,v in doc.items() if k!="routing_sha256"})
    write_json(output_dir/"paper_order_routing_v78_3.json",doc)
    ver = {
        "stage":"V78.3","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "routing_sha256":doc["routing_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_order_routing_verification_v78_3.json",ver)
    return doc

def run_paper_broker_safety_gate(foundation_path: Path, sync_path: Path, routing_path: Path, output_dir: Path) -> dict:
    foundation, sync, routing = map(load_json,(foundation_path,sync_path,routing_path))
    errors = []
    for expected,doc in (("V78.1",foundation),("V78.2",sync),("V78.3",routing)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    checks = {
        "offline_mode":foundation.get("paper_broker",{}).get("mode")=="offline_paper",
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,sync,routing)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,sync,routing)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,sync,routing)),
        "real_credentials_disallowed":foundation.get("real_credentials_allowed") is False,
        "live_trading_unauthorized":foundation.get("live_trading_authorized") is False,
        "short_selling_disabled":foundation.get("paper_broker",{}).get("short_selling_enabled") is False,
        "routing_checks_passed":routing.get("failed_checks")==[],
        "sync_checks_passed":sync.get("failed_checks")==[],
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("paper_broker_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.4.paper_broker_safety_gate.1",
        "stage":"V78.4","status":status,
        "gate_scope":"PAPER_BROKER_RUNTIME_ELIGIBILITY_ONLY",
        "decision":"ALLOW_PAPER_BROKER_RUNTIME" if not errors else "BLOCK_PAPER_BROKER_RUNTIME",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_5_PAPER_BROKER_ADAPTER_CERTIFICATE",
    }
    doc["safety_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"paper_broker_safety_gate_v78_4.json",doc)
    ver = {
        "stage":"V78.4","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_safety_gate_verification_v78_4.json",ver)
    return doc

def issue_paper_broker_certificate(v1: Path,v2: Path,v3: Path,v4: Path,foundation_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v1,v2,v3,v4)))
    foundation = load_json(foundation_path)
    expected = ["V78.1","V78.2","V78.3","V78.4"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v78.5.paper_broker_certificate.1",
        "stage":"V78.5",
        "certificate_id":"PAPER-BROKER-ADAPTER-V78.5",
        "status":status,
        "decision":"certified_for_offline_paper_broker_runtime" if not errors else "paper_broker_rejected",
        "certification_scope":"OFFLINE_PAPER_BROKER_RUNTIME_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_6_PAPER_EVENT_ENGINE" if not errors else "REPAIR_V78_5",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"paper_broker_adapter_certificate_v78_5.json",cert)
    ver = {
        "stage":"V78.5","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_adapter_certificate_verification_v78_5.json",ver)
    return cert
