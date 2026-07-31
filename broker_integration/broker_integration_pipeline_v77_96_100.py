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
class BrokerAccount:
    account_id: str
    currency: str
    cash: float
    buying_power: float
    equity: float
    status: str = "OFFLINE_SIMULATED"

@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: int
    average_price: float
    market_value: float

@dataclass(frozen=True)
class BrokerOrder:
    order_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    status: str
    limit_price: float | None = None

@dataclass(frozen=True)
class BrokerFill:
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    status: str = "SIMULATED_FILL"

@runtime_checkable
class BrokerInterface(Protocol):
    def get_account(self) -> BrokerAccount: ...
    def list_positions(self) -> list[BrokerPosition]: ...
    def submit_order(self, symbol: str, side: str, quantity: int,
                     order_type: str = "market", limit_price: float | None = None) -> BrokerOrder: ...
    def cancel_order(self, order_id: str) -> BrokerOrder: ...
    def list_orders(self) -> list[BrokerOrder]: ...
    def list_fills(self) -> list[BrokerFill]: ...
    def health(self) -> dict: ...

class OfflineBrokerAdapter:
    def __init__(self, starting_cash: float = 100000.0):
        self._cash = float(starting_cash)
        self._positions: dict[str, BrokerPosition] = {}
        self._orders: dict[str, BrokerOrder] = {}
        self._fills: list[BrokerFill] = []
        self._order_seq = 0
        self._fill_seq = 0
        self.network_allowed = False
        self.broker_connected = False
        self.real_credentials_loaded = False
        self.live_order_submission_enabled = False

    def get_account(self) -> BrokerAccount:
        market_value = sum(p.market_value for p in self._positions.values())
        equity = self._cash + market_value
        return BrokerAccount(
            account_id="OFFLINE-BROKER-V77-100",
            currency="USD",
            cash=round(self._cash, 8),
            buying_power=round(self._cash, 8),
            equity=round(equity, 8),
        )

    def list_positions(self) -> list[BrokerPosition]:
        return [self._positions[k] for k in sorted(self._positions)]

    def list_orders(self) -> list[BrokerOrder]:
        return [self._orders[k] for k in sorted(self._orders)]

    def list_fills(self) -> list[BrokerFill]:
        return list(self._fills)

    def health(self) -> dict:
        return {
            "adapter":"OfflineBrokerAdapter",
            "status":"HEALTHY",
            "environment":"offline",
            "network_allowed":False,
            "broker_connected":False,
            "real_credentials_loaded":False,
            "live_order_submission_enabled":False,
        }

    def submit_order(self, symbol: str, side: str, quantity: int,
                     order_type: str = "market", limit_price: float | None = None) -> BrokerOrder:
        symbol = str(symbol).upper().strip()
        side = str(side).lower().strip()
        order_type = str(order_type).lower().strip()
        if not symbol:
            raise ValueError("symbol is required")
        if side not in ("buy","sell"):
            raise ValueError("side must be buy or sell")
        if int(quantity) <= 0:
            raise ValueError("quantity must be positive")
        if order_type not in ("market","limit"):
            raise ValueError("unsupported order type")
        if order_type == "limit" and (limit_price is None or float(limit_price) <= 0):
            raise ValueError("positive limit_price required")
        if side == "sell":
            held = self._positions.get(symbol)
            if held is None or held.quantity < int(quantity):
                raise ValueError("short selling disabled")

        self._order_seq += 1
        order_id = f"OFFLINE-ORD-{self._order_seq:08d}"
        order = BrokerOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=int(quantity),
            order_type=order_type,
            status="ACCEPTED_OFFLINE_ONLY",
            limit_price=float(limit_price) if limit_price is not None else None,
        )
        self._orders[order_id] = order
        return order

    def simulate_fill(self, order_id: str, price: float, quantity: int | None = None) -> BrokerFill:
        if order_id not in self._orders:
            raise ValueError("unknown order")
        order = self._orders[order_id]
        if order.status in ("FILLED","CANCELED"):
            raise ValueError("order is terminal")
        fill_qty = order.quantity if quantity is None else int(quantity)
        if fill_qty <= 0 or fill_qty > order.quantity:
            raise ValueError("invalid fill quantity")
        price = float(price)
        if price <= 0:
            raise ValueError("price must be positive")
        notional = fill_qty * price

        if order.side == "buy":
            if notional > self._cash:
                raise ValueError("insufficient simulated cash")
            self._cash -= notional
            previous = self._positions.get(order.symbol)
            old_qty = previous.quantity if previous else 0
            old_cost = previous.average_price * old_qty if previous else 0.0
            new_qty = old_qty + fill_qty
            avg = (old_cost + notional) / new_qty
            self._positions[order.symbol] = BrokerPosition(
                symbol=order.symbol, quantity=new_qty,
                average_price=round(avg,8), market_value=round(new_qty*price,8)
            )
        else:
            previous = self._positions[order.symbol]
            new_qty = previous.quantity - fill_qty
            self._cash += notional
            if new_qty == 0:
                del self._positions[order.symbol]
            else:
                self._positions[order.symbol] = BrokerPosition(
                    symbol=order.symbol, quantity=new_qty,
                    average_price=previous.average_price,
                    market_value=round(new_qty*price,8)
                )

        self._fill_seq += 1
        fill = BrokerFill(
            fill_id=f"OFFLINE-FILL-{self._fill_seq:08d}",
            order_id=order_id, symbol=order.symbol, side=order.side,
            quantity=fill_qty, price=price
        )
        self._fills.append(fill)
        self._orders[order_id] = BrokerOrder(
            order_id=order.order_id, symbol=order.symbol, side=order.side,
            quantity=order.quantity, order_type=order.order_type,
            status="FILLED", limit_price=order.limit_price
        )
        return fill

    def cancel_order(self, order_id: str) -> BrokerOrder:
        if order_id not in self._orders:
            raise ValueError("unknown order")
        order = self._orders[order_id]
        if order.status == "FILLED":
            raise ValueError("filled order cannot be canceled")
        canceled = BrokerOrder(
            order_id=order.order_id, symbol=order.symbol, side=order.side,
            quantity=order.quantity, order_type=order.order_type,
            status="CANCELED", limit_price=order.limit_price
        )
        self._orders[order_id] = canceled
        return canceled

def build_broker_integration_skeleton(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors = []
    if cert.get("stage")!="V77.95" or cert.get("status")!="PASS":
        errors.append("live_readiness_certificate")
    if cert.get("certification_scope")!="BROKER_INTEGRATION_SKELETON_ELIGIBILITY_ONLY":
        errors.append("certificate_scope")
    if cert.get("broker_connection_approved") is not False:
        errors.append("broker_connection_must_remain_disabled")
    if cert.get("actual_order_submission_allowed") is not False:
        errors.append("actual_orders_must_remain_disabled")
    skeleton = config.get("broker_skeleton",{})
    required = ("adapter_name","mode","network_policy","credential_policy","order_submission_policy")
    for key in required:
        if key not in skeleton:
            errors.append(f"config_{key}")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.96.broker_integration_skeleton.1",
        "stage":"V77.96","status":status,
        "integration_scope":"OFFLINE_INTERFACE_SKELETON_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "broker_skeleton":skeleton,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_97_BROKER_INTERFACE_CONTRACT",
    }
    doc["broker_skeleton_sha256"] = digest_json({k:v for k,v in doc.items() if k!="broker_skeleton_sha256"})
    write_json(output_dir/"broker_integration_skeleton_v77_96.json",doc)
    ver = {
        "stage":"V77.96","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "broker_skeleton_sha256":doc["broker_skeleton_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"broker_integration_skeleton_verification_v77_96.json",ver)
    return doc

def build_broker_interface_contract(skeleton_path: Path, output_dir: Path) -> dict:
    skeleton = load_json(skeleton_path)
    errors = []
    if skeleton.get("stage")!="V77.96" or skeleton.get("status")!="PASS":
        errors.append("skeleton_input")
    methods = {
        "get_account":{"returns":"BrokerAccount"},
        "list_positions":{"returns":"list[BrokerPosition]"},
        "submit_order":{"returns":"BrokerOrder","offline_only":True},
        "cancel_order":{"returns":"BrokerOrder"},
        "list_orders":{"returns":"list[BrokerOrder]"},
        "list_fills":{"returns":"list[BrokerFill]"},
        "health":{"returns":"dict"},
    }
    models = {
        "BrokerAccount":["account_id","currency","cash","buying_power","equity","status"],
        "BrokerPosition":["symbol","quantity","average_price","market_value"],
        "BrokerOrder":["order_id","symbol","side","quantity","order_type","status","limit_price"],
        "BrokerFill":["fill_id","order_id","symbol","side","quantity","price","status"],
    }
    if not isinstance(OfflineBrokerAdapter(), BrokerInterface):
        errors.append("protocol_compliance")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.97.broker_interface_contract.1",
        "stage":"V77.97","status":status,
        "contract_name":"BrokerInterface",
        "methods":methods,"models":models,
        "real_broker_implementation_present":False,
        "network_transport_present":False,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_98_OFFLINE_BROKER_ADAPTER_HARNESS",
    }
    doc["contract_sha256"] = digest_json({k:v for k,v in doc.items() if k!="contract_sha256"})
    write_json(output_dir/"broker_interface_contract_v77_97.json",doc)
    ver = {
        "stage":"V77.97","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "contract_sha256":doc["contract_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"broker_interface_contract_verification_v77_97.json",ver)
    return doc

def run_offline_broker_adapter_harness(contract_path: Path, output_dir: Path) -> dict:
    contract = load_json(contract_path)
    errors = []
    if contract.get("stage")!="V77.97" or contract.get("status")!="PASS":
        errors.append("contract_input")
    adapter = OfflineBrokerAdapter(starting_cash=100000.0)
    events = []
    try:
        buy = adapter.submit_order("AAPL","buy",10)
        events.append({"event":"ORDER_ACCEPTED","payload":asdict(buy)})
        fill1 = adapter.simulate_fill(buy.order_id,100.0)
        events.append({"event":"SIMULATED_FILL","payload":asdict(fill1)})
        sell = adapter.submit_order("AAPL","sell",4)
        events.append({"event":"ORDER_ACCEPTED","payload":asdict(sell)})
        fill2 = adapter.simulate_fill(sell.order_id,110.0)
        events.append({"event":"SIMULATED_FILL","payload":asdict(fill2)})
        cancel = adapter.submit_order("MSFT","buy",1,order_type="limit",limit_price=200.0)
        canceled = adapter.cancel_order(cancel.order_id)
        events.append({"event":"ORDER_CANCELED","payload":asdict(canceled)})
    except Exception as exc:
        errors.append(f"harness_exception:{type(exc).__name__}")

    account = asdict(adapter.get_account())
    positions = [asdict(x) for x in adapter.list_positions()]
    orders = [asdict(x) for x in adapter.list_orders()]
    fills = [asdict(x) for x in adapter.list_fills()]
    health = adapter.health()
    checks = {
        "cash_expected":account["cash"]==99440.0,
        "position_expected":positions==[{"symbol":"AAPL","quantity":6,"average_price":100.0,"market_value":660.0}],
        "order_count_expected":len(orders)==3,
        "fill_count_expected":len(fills)==2,
        "network_disabled":health["network_allowed"] is False,
        "broker_disconnected":health["broker_connected"] is False,
        "credentials_absent":health["real_credentials_loaded"] is False,
        "live_submission_disabled":health["live_order_submission_enabled"] is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("offline_harness_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.98.offline_broker_adapter_harness.1",
        "stage":"V77.98","status":status,
        "adapter":"OfflineBrokerAdapter",
        "events":events,"account":account,"positions":positions,
        "orders":orders,"fills":fills,"health":health,
        "checks":checks,"failed_checks":failed,
        "actual_orders_submitted":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_99_BROKER_INTEGRATION_SAFETY_GATE",
    }
    doc["harness_sha256"] = digest_json({k:v for k,v in doc.items() if k!="harness_sha256"})
    write_json(output_dir/"offline_broker_adapter_harness_v77_98.json",doc)
    ver = {
        "stage":"V77.98","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "harness_sha256":doc["harness_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"offline_broker_adapter_harness_verification_v77_98.json",ver)
    return doc

def run_broker_integration_safety_gate(skeleton_path: Path, contract_path: Path, harness_path: Path, output_dir: Path) -> dict:
    skeleton, contract, harness = map(load_json,(skeleton_path,contract_path,harness_path))
    errors = []
    for expected,doc in (("V77.96",skeleton),("V77.97",contract),("V77.98",harness)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    h = harness.get("health",{})
    checks = {
        "offline_environment":skeleton.get("environment")=="offline",
        "network_disabled":h.get("network_allowed") is False,
        "broker_disconnected":h.get("broker_connected") is False,
        "real_credentials_absent":h.get("real_credentials_loaded") is False,
        "live_submission_disabled":h.get("live_order_submission_enabled") is False,
        "actual_orders_zero":harness.get("actual_orders_submitted")==0,
        "real_broker_implementation_absent":contract.get("real_broker_implementation_present") is False,
        "network_transport_absent":contract.get("network_transport_present") is False,
        "live_trading_unauthorized":skeleton.get("live_trading_authorized") is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("broker_integration_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.99.broker_integration_safety_gate.1",
        "stage":"V77.99","status":status,
        "gate_scope":"OFFLINE_ADAPTER_DEVELOPMENT_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_ADAPTER_DEVELOPMENT" if not errors else "BLOCK_ADAPTER_DEVELOPMENT",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_100_BROKER_INTEGRATION_SKELETON_CERTIFICATE",
    }
    doc["safety_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"broker_integration_safety_gate_v77_99.json",doc)
    ver = {
        "stage":"V77.99","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"broker_integration_safety_gate_verification_v77_99.json",ver)
    return doc

def issue_broker_integration_certificate(v96: Path,v97: Path,v98: Path,v99: Path,skeleton_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v96,v97,v98,v99)))
    skeleton = load_json(skeleton_path)
    expected = ["V77.96","V77.97","V77.98","V77.99"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v77.100.broker_integration_certificate.1",
        "stage":"V77.100",
        "certificate_id":"BROKER-INTEGRATION-SKELETON-V77.100",
        "status":status,
        "decision":"certified_for_offline_broker_adapter_development" if not errors else "broker_skeleton_rejected",
        "certification_scope":"OFFLINE_BROKER_ADAPTER_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":skeleton.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_1_PAPER_BROKER_ADAPTER_FOUNDATION" if not errors else "REPAIR_V77_100",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"broker_integration_skeleton_certificate_v77_100.json",cert)
    ver = {
        "stage":"V77.100","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"broker_integration_skeleton_certificate_verification_v77_100.json",ver)
    return cert
