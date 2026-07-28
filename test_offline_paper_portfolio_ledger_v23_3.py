"""Standalone validation for V23.3 Offline Paper Portfolio Ledger."""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_ledger_v23_3 import (
    CONFIRMATION_TEXT,
    PortfolioValidationLedgerV233Policy,
    load_portfolio_validation_result,
    record_portfolio_validation_v23_3,
    save_portfolio_validation_result,
    sha256_payload,
    verify_portfolio_validation_ledger,
)


NOW = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    average_cost: float
    last_fill_price: float
    cost_basis: float

    def to_dict(self): return self.__dict__.copy()


@dataclass(frozen=True)
class Portfolio:
    portfolio_snapshot_id: str
    created_at: str
    cash_balance: float
    positions_market_value: float
    total_equity: float
    positions: tuple[Position, ...]
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
    portfolio_hash: str

    def to_dict(self):
        payload = self.__dict__.copy()
        payload["positions"] = [item.to_dict() for item in self.positions]
        return payload

    def payload_without_hash(self):
        payload = self.to_dict()
        payload.pop("portfolio_hash")
        return payload


@dataclass
class Source:
    version: str
    result_status: str
    all_checks_passed: bool
    update_result_id: str
    portfolio_hash: str
    portfolio: Portfolio
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
        payload["portfolio"] = self.portfolio.to_dict()
        return payload


def make_source(result_id="update-001"):
    position = Position("AAPL", 2.0, 100.0, 105.0, 200.0)
    payload = {
        "portfolio_snapshot_id": f"portfolio-{result_id}",
        "created_at": (NOW - timedelta(minutes=5)).isoformat(),
        "cash_balance": 800.0, "positions_market_value": 210.0,
        "total_equity": 1010.0, "positions": (position,),
        "funds_reserved": False, "holdings_reserved": False, "transmit": False,
        "credentials_used": False, "market_data_api_called": False,
        "account_api_called": False, "network_accessed": False,
        "broker_api_called": False, "broker_order_created": False,
        "order_submitted": False, "live_execution_authorized": False,
    }
    hash_payload = {**payload, "positions": [position.to_dict()]}
    portfolio = Portfolio(**payload, portfolio_hash=sha256_payload(hash_payload))
    return Source("V23.2", "UPDATED_IN_MEMORY", True, result_id,
                  portfolio.portfolio_hash, portfolio)


def run(source=None, ledger=None, now=NOW, confirmation=CONFIRMATION_TEXT,
        policy=None, operator="paper-operator"):
    return record_portfolio_validation_v23_3(
        source or make_source(), operator, confirmation,
        existing_ledger=ledger, policy=policy, now=now,
    )


def imports_are_safe():
    tree = ast.parse(Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_ledger_v23_3.py").read_text(encoding="utf-8"))
    forbidden = {"requests", "urllib", "httpx", "socket", "alpaca", "ibapi",
                 "ccxt", "boto3"}
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return not (names & forbidden)


first_source = make_source("update-001")
first_before = first_source.to_dict()
first = run(first_source)
second_source = make_source("update-002")
second = run(second_source, first.ledger, NOW + timedelta(minutes=1))

checks = {
    "Version is V23.3": first.version == "V23.3",
    "Default policy is valid": first.policy_checks_passed,
    "V23.2 source passed": first.source_checks_passed,
    "Accounting checks passed": first.accounting_checks_passed,
    "First validation was recorded": first.entry_recorded,
    "Second validation was recorded": second.entry_recorded,
    "Two ledger entries were created": len(second.ledger.entries) == 2,
    "Sequences are chronological": [x.sequence for x in second.ledger.entries] == [1, 2],
    "Ledger hash chain passed": not verify_portfolio_validation_ledger(second.ledger),
    "Source remained unchanged": first_source.to_dict() == first_before,
    "Duplicate validation was blocked": not run(first_source, first.ledger).all_checks_passed,
    "Wrong confirmation was blocked": not run(confirmation="WRONG").all_checks_passed,
    "Empty operator was blocked": not run(operator="").all_checks_passed,
    "Wrong source version failed": not run(replace(make_source(), version="V23.1")).all_checks_passed,
    "Backward time was blocked": not run(second_source, first.ledger, NOW - timedelta(seconds=1)).all_checks_passed,
    "Tampered portfolio failed": not run(replace(make_source(), portfolio_hash="f" * 64)).all_checks_passed,
    "Bad accounting failed": not run(replace(make_source(), portfolio=replace(make_source().portfolio, total_equity=999))).all_checks_passed,
    "Tampered ledger detected": bool(verify_portfolio_validation_ledger(
        replace(first.ledger, ledger_hash="0" * 64))),
    "Tampered existing ledger was blocked": not run(second_source, replace(
        first.ledger, ledger_hash="a" * 64)).all_checks_passed,
    "Invalid policy was blocked": not run(policy=replace(
        PortfolioValidationLedgerV233Policy(), network_access_disabled=False)).all_checks_passed,
    "Forbidden network broker imports are absent": imports_are_safe(),
    "Funds were not reserved": not first.funds_reserved,
    "Holdings were not reserved": not first.holdings_reserved,
    "Market data API was not called": not first.market_data_api_called,
    "Account API was not called": not first.account_api_called,
    "Network was not accessed": not first.network_accessed,
    "Broker API was not called": not first.broker_api_called,
    "Broker order was not created": not first.broker_order_created,
    "Order was not submitted": not first.order_submitted,
    "Live execution not authorized": not first.live_execution_authorized,
    "Execution remains blocked": first.execution_blocked,
}

with TemporaryDirectory() as directory:
    report, latest = save_portfolio_validation_result(first, directory)
    loaded = load_portfolio_validation_result(report)
    checks["Result save and load passed"] = (
        report.exists() and latest.exists() and loaded["version"] == "V23.3"
        and loaded["ledger_hash"] == first.ledger_hash
    )

checks["All checks passed"] = all(checks.values())
width = max(map(len, checks))
print("=" * (width + 12))
print("AI STOCK BOT V23.3 OFFLINE PAPER PORTFOLIO VALIDATION LEDGER TEST")
print("=" * (width + 12))
for name, passed in checks.items():
    print(f"{name:<{width}} : {passed}")
print("=" * (width + 12))
if not checks["All checks passed"]:
    raise AssertionError([name for name, passed in checks.items() if not passed])
print("\nV23.3 offline paper portfolio validation ledger test completed successfully.")
print("V23.2 Portfolio Hash, 회계 불변식, Ledger Sequence 및 SHA-256 Hash Chain이 검증되었습니다.")
print("Network, Broker API, 실제 주문 및 Live Execution은 호출되지 않았습니다.")
