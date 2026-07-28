"""Standalone validation for V23.4 Offline Paper Portfolio Ledger Audit."""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_ledger_v23_3 import (
    CONFIRMATION_TEXT as SOURCE_CONFIRMATION,
    record_portfolio_validation_v23_3,
    sha256_payload,
)
from backtest.offline_paper_portfolio_audit_v23_4 import (
    CONFIRMATION_TEXT,
    PortfolioLedgerAuditV234Policy,
    audit_portfolio_validation_ledger_v23_4,
    load_audit_result,
    save_audit_result,
    verify_audit_certificate,
)


NOW = datetime(2026, 7, 28, 23, 40, tzinfo=timezone.utc)


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
class SourceV232:
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


def make_update_source(result_id: str):
    position = Position("AAPL", 2.0, 100.0, 105.0, 200.0)
    payload = {
        "portfolio_snapshot_id": f"portfolio-{result_id}",
        "created_at": (NOW - timedelta(minutes=5)).isoformat(),
        "cash_balance": 800.0,
        "positions_market_value": 210.0,
        "total_equity": 1010.0,
        "positions": (position,),
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
    portfolio_hash = sha256_payload({
        **payload, "positions": [position.to_dict()],
    })
    portfolio = Portfolio(**payload, portfolio_hash=portfolio_hash)
    return SourceV232(
        "V23.2", "UPDATED_IN_MEMORY", True, result_id, portfolio_hash, portfolio,
    )


def make_v233_source():
    first = record_portfolio_validation_v23_3(
        make_update_source("update-001"),
        "paper-operator",
        SOURCE_CONFIRMATION,
        now=NOW - timedelta(minutes=2),
    )
    return record_portfolio_validation_v23_3(
        make_update_source("update-002"),
        "paper-operator",
        SOURCE_CONFIRMATION,
        existing_ledger=first.ledger,
        now=NOW - timedelta(minutes=1),
    )


def run(source=None, confirmation=CONFIRMATION_TEXT, operator="paper-auditor",
        policy=None, now=NOW):
    return audit_portfolio_validation_ledger_v23_4(
        source or make_v233_source(), operator, confirmation,
        policy=policy, now=now,
    )


def imports_are_safe():
    target = Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_audit_v23_4.py")
    tree = ast.parse(target.read_text(encoding="utf-8"))
    forbidden = {"requests", "urllib", "httpx", "socket", "alpaca", "ibapi",
                 "ccxt", "boto3"}
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return not (names & forbidden)


source = make_v233_source()
before = source.to_dict()
result = run(source)

tampered_entry = replace(source.ledger.entries[0], entry_hash="f" * 64)
tampered_ledger = replace(
    source.ledger,
    entries=(tampered_entry, *source.ledger.entries[1:]),
)
tampered_source = replace(source, ledger=tampered_ledger)
duplicate_entry = replace(
    source.ledger.entries[1],
    validation_id=source.ledger.entries[0].validation_id,
)
duplicate_source = replace(
    source,
    ledger=replace(source.ledger, entries=(source.ledger.entries[0], duplicate_entry)),
)

checks = {
    "Version is V23.4": result.version == "V23.4",
    "Default policy is valid": result.policy_checks_passed,
    "V23.3 source passed": result.source_checks_passed,
    "Ledger hash chain passed": result.ledger_checks_passed,
    "Two entry findings passed": len(result.certificate.findings) == 2,
    "Sequences are chronological": result.chronology_checks_passed,
    "Source linkage passed": result.source_linkage_checks_passed,
    "Entry safety passed": result.entry_safety_checks_passed,
    "Snapshot hash was created": len(result.source_ledger_snapshot_hash) == 64,
    "Audit certificate hash passed": not verify_audit_certificate(result.certificate),
    "Source remained unchanged": source.to_dict() == before,
    "Wrong confirmation was blocked": not run(confirmation="WRONG").all_checks_passed,
    "Empty operator was blocked": not run(operator="").all_checks_passed,
    "Wrong source version failed": not run(replace(source, version="V23.2")).all_checks_passed,
    "Backward time was blocked": not run(now=NOW - timedelta(minutes=3)).all_checks_passed,
    "Tampered ledger failed": not run(tampered_source).all_checks_passed,
    "Duplicate validation failed": not run(duplicate_source).all_checks_passed,
    "Tampered certificate detected": bool(verify_audit_certificate(
        replace(result.certificate, certificate_hash="0" * 64))),
    "Invalid policy was blocked": not run(policy=replace(
        PortfolioLedgerAuditV234Policy(), network_access_disabled=False)).all_checks_passed,
    "Forbidden network broker imports are absent": imports_are_safe(),
    "Ledger was not modified": not result.ledger_modified,
    "Funds were not reserved": not result.funds_reserved,
    "Holdings were not reserved": not result.holdings_reserved,
    "Market data API was not called": not result.market_data_api_called,
    "Account API was not called": not result.account_api_called,
    "Network was not accessed": not result.network_accessed,
    "Broker API was not called": not result.broker_api_called,
    "Broker order was not created": not result.broker_order_created,
    "Order was not submitted": not result.order_submitted,
    "Live execution not authorized": not result.live_execution_authorized,
    "Execution remains blocked": result.execution_blocked,
}

with TemporaryDirectory() as directory:
    report, latest = save_audit_result(result, directory)
    loaded = load_audit_result(report)
    checks["Result save and load passed"] = (
        report.exists()
        and latest.exists()
        and loaded["version"] == "V23.4"
        and loaded["audit_certificate_hash"] == result.audit_certificate_hash
    )

checks["All checks passed"] = all(checks.values())
width = max(map(len, checks))
print("=" * (width + 12))
print("AI STOCK BOT V23.4 OFFLINE PAPER PORTFOLIO LEDGER INTEGRITY AUDIT TEST")
print("=" * (width + 12))
for name, passed in checks.items():
    print(f"{name:<{width}} : {passed}")
print("=" * (width + 12))
if not checks["All checks passed"]:
    raise AssertionError([name for name, passed in checks.items() if not passed])
print("\nV23.4 offline paper portfolio ledger integrity audit test completed successfully.")
print("V23.3 Ledger Chain, Entry Findings, Snapshot Hash 및 Audit Certificate Hash가 검증되었습니다.")
print("잔액·보유수량 변경, Network, Broker 주문, 실제 주문 및 Live Execution은 호출되지 않았습니다.")
