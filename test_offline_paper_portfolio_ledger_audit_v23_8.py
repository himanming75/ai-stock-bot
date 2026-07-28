"""Standalone validation for V23.8 portfolio integrity ledger audit."""

from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_ledger_audit_v23_8 import (
    CONFIRMATION_TEXT,
    PortfolioLedgerAuditV238Policy,
    audit_portfolio_integrity_ledger_v23_8,
    load_audit_result,
    save_audit_result,
    verify_audit_certificate,
)
with contextlib.redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_integrity_ledger_v23_7 import (
        NOW, make_source, record)


def make_ledger():
    first = record(make_source(4), offset=5)
    return record(make_source(6), first.entries, offset=7)


def audit(source=None, operator="portfolio-ledger-auditor",
          confirmation=CONFIRMATION_TEXT, policy=None, offset=8):
    return audit_portfolio_integrity_ledger_v23_8(
        source if source is not None else make_ledger(),
        operator, confirmation, policy=policy,
        now=NOW + timedelta(seconds=offset))


def imports_are_safe():
    target = Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_ledger_audit_v23_8.py")
    tree = ast.parse(target.read_text(encoding="utf-8"))
    forbidden = {"requests", "urllib", "httpx", "socket", "alpaca",
                 "ibapi", "ccxt", "boto3"}
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return not names.intersection(forbidden)


def main():
    source = make_ledger()
    before = source.to_dict()
    result = audit(source)
    tampered = replace(
        source.entries[0], operator="attacker")
    duplicate = replace(
        source.entries[1], entry_id=source.entries[0].entry_id)

    checks = {
        "Version is V23.8": result.version == "V23.8",
        "Default policy is valid": result.policy_checks_passed,
        "V23.7 ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "Source remained unchanged": source.to_dict() == before,
        "Audit certificate was created":
            result.audit_certificate is not None,
        "Audit certificate hash passed":
            not verify_audit_certificate(result.audit_certificate),
        "Two entry findings passed":
            len(result.findings) == 2
            and all(f.finding_status == "PASSED" for f in result.findings),
        "Wrong confirmation was blocked":
            not audit(source, confirmation="WRONG").all_checks_passed,
        "Empty operator was blocked":
            not audit(source, operator="").all_checks_passed,
        "Wrong source type failed":
            not audit("bad-source").all_checks_passed,
        "Wrong source version failed":
            not audit(replace(source, version="V23.6")).all_checks_passed,
        "Wrong source status failed":
            not audit(replace(source, result_status="BLOCKED")).all_checks_passed,
        "Backward time was blocked":
            not audit(source, offset=6).all_checks_passed,
        "Tampered ledger failed":
            not audit(replace(
                source, entries=(tampered, source.entries[1]))).all_checks_passed,
        "Duplicate entry ID was detected":
            not audit(replace(
                source, entries=(source.entries[0], duplicate))).all_checks_passed,
        "Broken snapshot linkage was blocked":
            not audit(replace(
                source, ledger_snapshot_hash="f" * 64)).all_checks_passed,
        "Invalid policy was blocked":
            not audit(source, policy=replace(
                PortfolioLedgerAuditV238Policy(),
                network_access_disabled=False)).all_checks_passed,
        "Certificate tampering detected":
            bool(verify_audit_certificate(replace(
                result.audit_certificate, certificate_hash="f" * 64))),
        "Forbidden network/broker imports are absent": imports_are_safe(),
        "Ledger was not modified": not result.ledger_modified,
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": not result.market_data_api_called,
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized":
            not result.live_execution_authorized,
    }
    with TemporaryDirectory() as directory:
        report, latest = save_audit_result(result, directory)
        loaded = load_audit_result(report)
        checks["Result save and load passed"] = (
            report.exists() and latest.exists()
            and loaded["audit_result_id"] == result.audit_result_id)
    checks["All checks passed"] = all(checks.values())

    print("=" * 80)
    print("AI STOCK BOT V23.8 OFFLINE PAPER PORTFOLIO LEDGER AUDIT TEST")
    print("=" * 80)
    print("V23.8 VALIDATION CHECKS")
    print("-" * 80)
    for label, passed in checks.items():
        print(f"{label:<52} : {passed}")
    print("=" * 80)
    if not all(checks.values()):
        failed = [name for name, value in checks.items() if not value]
        raise AssertionError(f"V23.8 failed checks: {failed}")
    print("\nV23.8 offline paper portfolio ledger audit test completed successfully.")
    print("V23.7 Ledger Chain, Entry Findings, Snapshot Hash 및 Audit Certificate Hash가 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 없었습니다.")


if __name__ == "__main__":
    main()
