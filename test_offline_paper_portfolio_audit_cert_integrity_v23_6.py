"""Standalone validation for V23.6 ledger integrity audit."""

from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_audit_cert_integrity_v23_6 import (
    CONFIRMATION_TEXT,
    PortfolioAuditCertIntegrityV236Policy,
    audit_portfolio_audit_cert_ledger_v23_6,
    load_integrity_audit_result,
    save_integrity_audit_result,
    verify_integrity_audit_certificate,
)
from backtest.offline_paper_portfolio_audit_cert_ledger_v23_5 import (
    CONFIRMATION_TEXT as LEDGER_CONFIRMATION,
    ledger_snapshot_hash,
    record_portfolio_audit_certificate_v23_5,
)
with contextlib.redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_audit_cert_ledger_v23_5 import (
        NOW, make_audit)


def make_source():
    first = record_portfolio_audit_certificate_v23_5(
        make_audit(0), "paper-ledger", LEDGER_CONFIRMATION,
        now=NOW + timedelta(seconds=1))
    return record_portfolio_audit_certificate_v23_5(
        make_audit(2), "paper-ledger", LEDGER_CONFIRMATION,
        existing_entries=first.entries, now=NOW + timedelta(seconds=3))


def run(source=None, operator="integrity-auditor",
        confirmation=CONFIRMATION_TEXT, policy=None, offset=4):
    return audit_portfolio_audit_cert_ledger_v23_6(
        source if source is not None else make_source(),
        operator, confirmation, policy=policy,
        now=NOW + timedelta(seconds=offset))


def imports_are_safe():
    target = Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_audit_cert_integrity_v23_6.py")
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
    source = make_source()
    before = source.to_dict()
    result = run(source)
    bad_entry = replace(source.entries[0], operator="attacker")
    bad_link = replace(
        source.entries[0], source_ledger_hash="f" * 64)

    checks = {
        "Version is V23.6": result.version == "V23.6",
        "Default policy is valid": result.policy_checks_passed,
        "V23.5 ledger source passed": source.all_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Snapshot hash passed": result.snapshot_hash_checks_passed,
        "Latest entry hash passed": result.latest_hash_checks_passed,
        "Entry count passed": result.entry_count_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Chronology passed": result.chronology_checks_passed,
        "Source remained unchanged":
            source.to_dict() == before and not result.source_modified,
        "Integrity certificate was created":
            result.audit_completed and result.certificate is not None,
        "Certificate SHA-256 hash passed":
            not verify_integrity_audit_certificate(result.certificate),
        "Two entry findings passed":
            result.certificate.source_total_entry_count == 2,
        "Wrong confirmation was blocked":
            not run(source, confirmation="WRONG").all_checks_passed,
        "Empty operator was blocked":
            not run(source, operator="").all_checks_passed,
        "Wrong source type failed":
            not run("bad-source").all_checks_passed,
        "Wrong source version failed":
            not run(replace(source, version="V23.4")).all_checks_passed,
        "Wrong source status failed":
            not run(replace(source, result_status="BLOCKED")).all_checks_passed,
        "Backward time was blocked":
            not run(source, offset=2).all_checks_passed,
        "Tampered ledger entry failed":
            not run(replace(source, entries=(
                bad_entry, source.entries[1]))).all_checks_passed,
        "Broken source linkage failed":
            not run(replace(source, entries=(
                bad_link, source.entries[1]))).all_checks_passed,
        "Tampered snapshot was detected":
            not run(replace(
                source, ledger_snapshot_hash="f" * 64)).all_checks_passed,
        "Tampered latest hash was detected":
            not run(replace(
                source, latest_entry_hash="f" * 64)).all_checks_passed,
        "Tampered entry count was detected":
            not run(replace(
                source, total_entry_count=99)).all_checks_passed,
        "Tampered certificate was detected":
            bool(verify_integrity_audit_certificate(replace(
                result.certificate, certificate_hash="f" * 64))),
        "Invalid policy was blocked":
            not run(source, policy=replace(
                PortfolioAuditCertIntegrityV236Policy(),
                network_access_disabled=False)).all_checks_passed,
        "Source snapshot is still reproducible":
            source.ledger_snapshot_hash == ledger_snapshot_hash(source.entries),
        "Forbidden network/broker imports are absent": imports_are_safe(),
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": not result.market_data_api_called,
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    with TemporaryDirectory() as directory:
        report, latest = save_integrity_audit_result(result, directory)
        loaded = load_integrity_audit_result(report)
        checks["Result save and load passed"] = (
            report.exists() and latest.exists()
            and loaded["certificate"]["certificate_hash"]
            == result.certificate.certificate_hash)
    checks["All checks passed"] = all(checks.values())

    print("=" * 80)
    print("AI STOCK BOT V23.6 OFFLINE PAPER PORTFOLIO AUDIT CERTIFICATE INTEGRITY TEST")
    print("=" * 80)
    print("V23.6 VALIDATION CHECKS")
    print("-" * 80)
    for label, passed in checks.items():
        print(f"{label:<52} : {passed}")
    print("=" * 80)
    if not all(checks.values()):
        failed = [name for name, value in checks.items() if not value]
        raise AssertionError(f"V23.6 failed checks: {failed}")
    print("\nV23.6 offline paper portfolio audit certificate integrity test completed successfully.")
    print("V23.5 Ledger Chain, Snapshot Hash, Latest Hash 및 Certificate Hash가 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 없었습니다.")


if __name__ == "__main__":
    main()
