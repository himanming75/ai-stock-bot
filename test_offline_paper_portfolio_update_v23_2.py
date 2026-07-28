"""Standalone validation for V23.2 Offline Paper Portfolio Update."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_update_v23_2 import (
    CONFIRMATION_TEXT,
    OfflinePaperPortfolioUpdateV232Policy,
    apply_offline_paper_portfolio_update_v23_2,
    load_portfolio_update_result,
    save_portfolio_update_result,
    sha256_payload,
    verify_offline_paper_portfolio,
)


NOW = datetime(2026, 7, 28, 22, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FakePosition:
    symbol: str
    quantity: float
    average_cost: float

    def to_dict(self):
        return self.__dict__.copy()


@dataclass(frozen=True)
class FakeAccount:
    account_id: str
    created_at: str
    account_mode: str
    operator: str
    currency: str
    cash_balance: float
    positions: tuple[FakePosition, ...]
    account_hash: str

    def payload_without_hash(self):
        payload = self.to_dict()
        payload.pop("account_hash")
        return payload

    def to_dict(self):
        payload = self.__dict__.copy()
        payload["positions"] = [item.to_dict() for item in self.positions]
        return payload


@dataclass
class FakeAccountResult:
    version: str
    result_status: str
    all_checks_passed: bool
    account_result_id: str
    account_hash: str
    account: FakeAccount
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
        payload = self.__dict__.copy()
        payload["account"] = self.account.to_dict()
        return payload


@dataclass(frozen=True)
class FakeFill:
    paper_fill_id: str
    created_at: str
    fill_mode: str
    fill_status: str
    operator: str
    symbol: str
    side: str
    filled_quantity: float
    simulated_fill_price: float | None
    net_cash_effect: float
    account_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    fill_hash: str

    def payload_without_hash(self):
        payload = self.__dict__.copy()
        payload.pop("fill_hash")
        return payload

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class FakeFillResult:
    version: str
    result_status: str
    all_checks_passed: bool
    fill_result_id: str
    fill_hash: str
    fill: FakeFill
    account_mutated: bool = False
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
        payload = self.__dict__.copy()
        payload["fill"] = self.fill.to_dict()
        return payload


def make_account(cash=1000, positions=()):
    payload = {
        "account_id": "paper-account-001",
        "created_at": (NOW - timedelta(hours=1)).isoformat(),
        "account_mode": "OFFLINE_PAPER",
        "operator": "paper-operator",
        "currency": "USD",
        "cash_balance": cash,
        "positions": tuple(positions),
    }
    hash_payload = {
        **payload,
        "positions": [position.to_dict() for position in positions],
    }
    account = FakeAccount(**payload, account_hash=sha256_payload(hash_payload))
    return FakeAccountResult(
        version="V21.0",
        result_status="CREATED_IN_MEMORY",
        all_checks_passed=True,
        account_result_id="account-result-001",
        account_hash=account.account_hash,
        account=account,
    )


def make_fill(
    side="BUY",
    status="FILLED",
    quantity=2,
    price=100.02,
    cash_effect=-200.14,
):
    payload = {
        "paper_fill_id": "paper-fill-001",
        "created_at": (NOW - timedelta(minutes=5)).isoformat(),
        "fill_mode": "OFFLINE_PAPER_SIMULATION",
        "fill_status": status,
        "operator": "paper-operator",
        "symbol": "AAPL",
        "side": side,
        "filled_quantity": quantity if status == "FILLED" else 0,
        "simulated_fill_price": price if status == "FILLED" else None,
        "net_cash_effect": cash_effect if status == "FILLED" else 0,
        "account_mutated": False,
        "funds_reserved": False,
        "holdings_reserved": False,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    fill = FakeFill(**payload, fill_hash=sha256_payload(payload))
    return FakeFillResult(
        version="V23.1",
        result_status="SIMULATED_IN_MEMORY",
        all_checks_passed=True,
        fill_result_id="fill-result-001",
        fill_hash=fill.fill_hash,
        fill=fill,
    )


def run(account=None, fill=None, confirmation=CONFIRMATION_TEXT, now=NOW):
    return apply_offline_paper_portfolio_update_v23_2(
        account or make_account(),
        fill or make_fill(),
        "paper-operator",
        confirmation,
        now=now,
    )


def blocked(call):
    try:
        result = call()
        return result.result_status == "BLOCKED" and not result.all_checks_passed
    except Exception:
        return False


checks = {}
account = make_account()
fill = make_fill()
account_before = account.to_dict()
fill_before = fill.to_dict()
buy = run(account, fill)
checks["Version is V23.2"] = buy.version == "V23.2"
checks["Market buy was applied in memory"] = (
    buy.result_status == "UPDATED_IN_MEMORY"
    and buy.update_applied
    and buy.portfolio.update_status == "APPLIED"
)
checks["Buy cash was updated"] = buy.portfolio.cash_balance == 799.86
checks["Buy position was created"] = (
    len(buy.portfolio.positions) == 1
    and buy.portfolio.positions[0].symbol == "AAPL"
    and buy.portfolio.positions[0].quantity == 2
    and buy.portfolio.positions[0].average_cost == 100.02
)
valid, _ = verify_offline_paper_portfolio(buy.portfolio)
checks["Portfolio SHA-256 hash passed"] = valid
checks["Sources remained unchanged"] = (
    account.to_dict() == account_before and fill.to_dict() == fill_before
)

existing = FakePosition("AAPL", 2, 90)
average_buy = run(make_account(1000, (existing,)), make_fill())
checks["Weighted average cost passed"] = (
    average_buy.portfolio.positions[0].quantity == 4
    and average_buy.portfolio.positions[0].average_cost == 95.01
)

sell = run(
    make_account(500, (FakePosition("AAPL", 3, 90),)),
    make_fill(side="SELL", quantity=2, price=99.98, cash_effect=199.86),
)
checks["Sell cash and holdings passed"] = (
    sell.portfolio.cash_balance == 699.86
    and sell.portfolio.positions[0].quantity == 1
    and sell.portfolio.positions[0].average_cost == 90
)

closed = run(
    make_account(500, (FakePosition("AAPL", 2, 90),)),
    make_fill(side="SELL", quantity=2, price=99.98, cash_effect=199.86),
)
checks["Full sell removed position"] = len(closed.portfolio.positions) == 0

not_filled = run(fill=make_fill(status="NOT_FILLED"))
checks["Unfilled order made no portfolio change"] = (
    not_filled.result_status == "NO_CHANGE_IN_MEMORY"
    and not not_filled.update_applied
    and not_filled.portfolio.cash_balance == 1000
    and len(not_filled.portfolio.positions) == 0
)
checks["Insufficient cash was blocked"] = blocked(
    lambda: run(make_account(100), make_fill())
)
checks["Short selling was blocked"] = blocked(
    lambda: run(
        make_account(),
        make_fill(side="SELL", quantity=1, price=100, cash_effect=99.95),
    )
)
checks["Excess sell quantity was blocked"] = blocked(
    lambda: run(
        make_account(500, (FakePosition("AAPL", 1, 90),)),
        make_fill(side="SELL", quantity=2, price=100, cash_effect=199.90),
    )
)
checks["Wrong confirmation was blocked"] = blocked(
    lambda: run(confirmation="WRONG")
)
checks["Backward time was blocked"] = blocked(
    lambda: run(now=NOW - timedelta(hours=2))
)

tampered_account = make_account()
object.__setattr__(tampered_account.account, "cash_balance", 999999)
checks["Tampered account failed"] = blocked(lambda: run(tampered_account, make_fill()))
tampered_fill = make_fill()
object.__setattr__(tampered_fill.fill, "filled_quantity", 99)
checks["Tampered fill failed"] = blocked(lambda: run(make_account(), tampered_fill))
broken_account_link = make_account()
broken_account_link.account_hash = "0" * 64
checks["Broken account linkage failed"] = blocked(
    lambda: run(broken_account_link, make_fill())
)
broken_fill_link = make_fill()
broken_fill_link.fill_hash = "0" * 64
checks["Broken fill linkage failed"] = blocked(
    lambda: run(make_account(), broken_fill_link)
)
unsafe_fill = make_fill()
unsafe_fill.network_accessed = True
checks["Unsafe source failed"] = blocked(lambda: run(make_account(), unsafe_fill))
checks["Invalid policy was blocked"] = blocked(
    lambda: apply_offline_paper_portfolio_update_v23_2(
        make_account(),
        make_fill(),
        "paper-operator",
        CONFIRMATION_TEXT,
        policy=OfflinePaperPortfolioUpdateV232Policy(
            network_access_disabled=False
        ),
        now=NOW,
    )
)

with TemporaryDirectory() as directory:
    path = save_portfolio_update_result(buy, Path(directory))
    loaded = load_portfolio_update_result(path)
    checks["Result save and load passed"] = (
        loaded["version"] == "V23.2"
        and loaded["portfolio"]["portfolio_hash"] == buy.portfolio_hash
    )

checks["Original account was not mutated"] = (
    not buy.account_mutated and account.to_dict() == account_before
)
checks["Funds were not reserved"] = not buy.funds_reserved
checks["Holdings were not reserved"] = not buy.holdings_reserved
checks["Market data API was not called"] = not buy.market_data_api_called
checks["Account API was not called"] = not buy.account_api_called
checks["Network was not accessed"] = not buy.network_accessed
checks["Broker API was not called"] = not buy.broker_api_called
checks["Broker order was not created"] = not buy.broker_order_created
checks["Order was not submitted"] = not buy.order_submitted
checks["Live execution not authorized"] = not buy.live_execution_authorized
checks["Execution remains blocked"] = buy.execution_blocked

source_path = (
    Path(__file__).parent
    / "backtest"
    / "offline_paper_portfolio_update_v23_2.py"
)
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
    "requests",
    "httpx",
    "urllib",
    "socket",
    "websocket",
    "aiohttp",
    "alpaca",
    "ib_insync",
    "ccxt",
    "boto3",
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
print("AI STOCK BOT V23.2 OFFLINE PAPER PORTFOLIO UPDATE TEST")
print("=" * 80)
for name, value in checks.items():
    print(f"{name:<{width}} : {value}")
print("=" * 80)
if not checks["All checks passed"]:
    failed = [name for name, value in checks.items() if not value]
    raise AssertionError(f"V23.2 checks failed: {failed}")
print()
print("V23.2 offline paper portfolio update test completed successfully.")
print("가상 체결의 현금·보유수량·평균단가 반영과 Portfolio Hash가 검증되었습니다.")
print("원본 계좌 변경, Network, Broker 주문 및 Live Execution은 없었습니다.")
