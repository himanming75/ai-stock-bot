"""Standalone validation for V23.1 Offline Paper Fill Engine."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_fill_engine_v23_1 import (
    CONFIRMATION_TEXT,
    OfflinePaperFillEngineV231Policy,
    load_fill_result,
    save_fill_result,
    sha256_payload,
    simulate_offline_paper_fill_v23_1,
    verify_offline_paper_fill,
)


NOW = datetime(2026, 7, 28, 20, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FakeOrder:
    paper_order_id: str
    created_at: str
    order_mode: str
    order_status: str
    operator: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    order_hash: str

    def payload_without_hash(self):
        value = self.__dict__.copy()
        value.pop("order_hash")
        return value

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class FakeOrderResult:
    version: str
    result_status: str
    all_checks_passed: bool
    order_result_id: str
    order_hash: str
    order: FakeOrder
    funds_reserved: bool = False
    holdings_reserved: bool = False
    transmit: bool = False
    credentials_used: bool = False
    market_data_api_called: bool = False
    account_api_called: bool = False
    network_accessed: bool = False
    broker_api_called: bool = False
    broker_order_created: bool = False
    order_submitted: bool = False
    live_execution_authorized: bool = False

    def to_dict(self):
        value = self.__dict__.copy()
        value["order"] = self.order.to_dict()
        return value


@dataclass(frozen=True)
class FakeAuditCertificate:
    integrity_certificate_id: str
    audited_at: str
    audit_status: str
    certificate_hash: str

    def payload_without_hash(self):
        value = self.__dict__.copy()
        value.pop("certificate_hash")
        return value

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class FakeAuditResult:
    version: str
    result_status: str
    all_checks_passed: bool
    audit_completed: bool
    audit_result_id: str
    integrity_certificate_hash: str
    certificate: FakeAuditCertificate
    ledger_modified: bool = False
    funds_reserved: bool = False
    holdings_reserved: bool = False
    market_data_api_called: bool = False
    account_api_called: bool = False
    network_accessed: bool = False
    broker_api_called: bool = False
    broker_order_created: bool = False
    order_submitted: bool = False
    live_execution_authorized: bool = False

    def to_dict(self):
        value = self.__dict__.copy()
        value["certificate"] = self.certificate.to_dict()
        return value


def make_order(side="BUY", order_type="MARKET", limit_price=None):
    payload = {
        "paper_order_id": "paper-order-001",
        "created_at": (NOW - timedelta(minutes=10)).isoformat(),
        "order_mode": "OFFLINE_PAPER_DRAFT",
        "order_status": "DRAFTED_IN_MEMORY",
        "operator": "paper-operator",
        "symbol": "AAPL",
        "side": side,
        "order_type": order_type,
        "quantity": 2.0,
        "limit_price": limit_price,
    }
    order = FakeOrder(**payload, order_hash=sha256_payload(payload))
    return FakeOrderResult(
        version="V21.1",
        result_status="DRAFTED_IN_MEMORY",
        all_checks_passed=True,
        order_result_id="order-result-001",
        order_hash=order.order_hash,
        order=order,
    )


def make_audit():
    payload = {
        "integrity_certificate_id": "audit-cert-001",
        "audited_at": (NOW - timedelta(minutes=5)).isoformat(),
        "audit_status": "PASSED",
    }
    certificate = FakeAuditCertificate(
        **payload, certificate_hash=sha256_payload(payload)
    )
    return FakeAuditResult(
        version="V23.0",
        result_status="AUDITED_IN_MEMORY",
        all_checks_passed=True,
        audit_completed=True,
        audit_result_id="audit-result-001",
        integrity_certificate_hash=certificate.certificate_hash,
        certificate=certificate,
    )


def run(order, audit, price=100, now=NOW, confirmation=CONFIRMATION_TEXT):
    return simulate_offline_paper_fill_v23_1(
        order,
        audit,
        "paper-operator",
        confirmation,
        price,
        now=now,
    )


def blocked(call):
    try:
        result = call()
        return result.result_status == "BLOCKED" and not result.all_checks_passed
    except Exception:
        return False


checks = {}
order = make_order()
audit = make_audit()
order_before = order.to_dict()
audit_before = audit.to_dict()
market_buy = run(order, audit)
checks["Version is V23.1"] = market_buy.version == "V23.1"
checks["Market buy fill was simulated"] = (
    market_buy.result_status == "SIMULATED_IN_MEMORY"
    and market_buy.fill_status == "FILLED"
    and market_buy.fill.filled_quantity == 2.0
)
checks["Buy slippage was applied"] = market_buy.fill.simulated_fill_price == 100.02
checks["Fee and cash effect passed"] = (
    market_buy.fill.gross_notional == 200.04
    and market_buy.fill.simulated_fee == 0.10
    and market_buy.fill.net_cash_effect == -200.14
)
valid_fill, _ = verify_offline_paper_fill(market_buy.fill)
checks["Fill SHA-256 hash passed"] = valid_fill
checks["Sources remained unchanged"] = (
    order.to_dict() == order_before and audit.to_dict() == audit_before
)

limit_buy = run(make_order(order_type="LIMIT", limit_price=101), make_audit(), 100)
checks["Marketable limit buy filled"] = (
    limit_buy.fill_status == "FILLED"
    and limit_buy.fill.simulated_fill_price <= 101
)
not_filled = run(make_order(order_type="LIMIT", limit_price=99), make_audit(), 100)
checks["Non-marketable limit remained unfilled"] = (
    not_filled.all_checks_passed
    and not_filled.fill_status == "NOT_FILLED"
    and not_filled.fill.filled_quantity == 0
    and not_filled.fill.gross_notional == 0
)
sell = run(make_order(side="SELL"), make_audit(), 100)
checks["Market sell fill passed"] = (
    sell.fill_status == "FILLED"
    and sell.fill.simulated_fill_price == 99.98
    and sell.fill.net_cash_effect == 199.86
)

checks["Wrong confirmation was blocked"] = blocked(
    lambda: run(make_order(), make_audit(), confirmation="WRONG")
)
checks["Invalid offline prices were blocked"] = all(
    blocked(lambda value=value: run(make_order(), make_audit(), value))
    for value in (0, -1, True, "nan", "inf", object())
)
checks["Backward time was blocked"] = blocked(
    lambda: run(make_order(), make_audit(), now=NOW - timedelta(hours=1))
)

tampered_order = make_order()
object.__setattr__(tampered_order.order, "quantity", 99)
checks["Tampered order failed"] = blocked(lambda: run(tampered_order, make_audit()))
tampered_audit = make_audit()
object.__setattr__(tampered_audit.certificate, "audit_status", "ALTERED")
checks["Tampered audit certificate failed"] = blocked(
    lambda: run(make_order(), tampered_audit)
)
bad_order_link = make_order()
bad_order_link.order_hash = "0" * 64
checks["Broken order result linkage failed"] = blocked(
    lambda: run(bad_order_link, make_audit())
)
bad_audit_link = make_audit()
bad_audit_link.integrity_certificate_hash = "0" * 64
checks["Broken audit result linkage failed"] = blocked(
    lambda: run(make_order(), bad_audit_link)
)
unsafe_order = make_order()
unsafe_order.network_accessed = True
checks["Unsafe source failed"] = blocked(lambda: run(unsafe_order, make_audit()))
checks["Invalid policies were blocked"] = blocked(
    lambda: simulate_offline_paper_fill_v23_1(
        make_order(),
        make_audit(),
        "paper-operator",
        CONFIRMATION_TEXT,
        100,
        policy=OfflinePaperFillEngineV231Policy(network_access_disabled=False),
        now=NOW,
    )
)

with TemporaryDirectory() as directory:
    path = save_fill_result(market_buy, Path(directory))
    loaded = load_fill_result(path)
    checks["Result save and load passed"] = (
        loaded["version"] == "V23.1"
        and loaded["fill"]["fill_hash"] == market_buy.fill_hash
    )

checks["Account was not mutated"] = not market_buy.account_mutated
checks["Funds were not reserved"] = not market_buy.funds_reserved
checks["Holdings were not reserved"] = not market_buy.holdings_reserved
checks["Market data API was not called"] = not market_buy.market_data_api_called
checks["Account API was not called"] = not market_buy.account_api_called
checks["Network was not accessed"] = not market_buy.network_accessed
checks["Broker API was not called"] = not market_buy.broker_api_called
checks["Broker order was not created"] = not market_buy.broker_order_created
checks["Order was not submitted"] = not market_buy.order_submitted
checks["Live execution not authorized"] = not market_buy.live_execution_authorized
checks["Execution remains blocked"] = market_buy.execution_blocked

source_path = Path(__file__).parent / "backtest" / "offline_paper_fill_engine_v23_1.py"
tree = ast.parse(source_path.read_text(encoding="utf-8"))
imports = {
    alias.name.split(".")[0]
    for node in ast.walk(tree)
    if isinstance(node, ast.Import)
    for alias in node.names
}
imports.update(
    node.module.split(".")[0]
    for node in ast.walk(tree)
    if isinstance(node, ast.ImportFrom) and node.module
)
forbidden_imports = {
    "requests", "httpx", "urllib", "socket", "websocket", "aiohttp",
    "alpaca", "ib_insync", "ccxt", "boto3",
}
checks["Forbidden network/broker imports are absent"] = not (
    imports & forbidden_imports
)
source_text = source_path.read_text(encoding="utf-8").lower()
forbidden_calls = (".post(", ".put(", ".delete(", "submit_order(", "place_order(")
checks["External execution calls are absent"] = not any(
    token in source_text for token in forbidden_calls
)
checks["All checks passed"] = all(checks.values())

width = max(len(name) for name in checks)
print("=" * 80)
print("AI STOCK BOT V23.1 OFFLINE PAPER FILL ENGINE TEST")
print("=" * 80)
for name, value in checks.items():
    print(f"{name:<{width}} : {value}")
print("=" * 80)
if not checks["All checks passed"]:
    failed = [name for name, value in checks.items() if not value]
    raise AssertionError(f"V23.1 checks failed: {failed}")
print()
print("V23.1 offline paper fill engine test completed successfully.")
print("오프라인 가격 기반 체결·미체결, Slippage, Fee, Fill Hash가 검증되었습니다.")
print("계좌·잔액·보유수량 변경, Network, Broker 주문 및 Live Execution은 없었습니다.")
