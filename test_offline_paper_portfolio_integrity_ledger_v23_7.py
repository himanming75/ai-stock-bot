"""Standalone validation for V23.7 integrity certificate ledger."""

from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_integrity_ledger_v23_7 import (
    CONFIRMATION_TEXT,
    PortfolioIntegrityLedgerV237Policy,
    ledger_snapshot_hash,
    load_ledger_result,
    record_integrity_certificate_v23_7,
    save_ledger_result,
    verify_integrity_certificate_ledger,
)
with contextlib.redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_audit_cert_integrity_v23_6 import (
        NOW, run as make_integrity_audit)


def make_source(offset=4):
    return make_integrity_audit(offset=offset)


def record(source=None, entries=None, operator="integrity-ledger",
           confirmation=CONFIRMATION_TEXT, policy=None, offset=5):
    return record_integrity_certificate_v23_7(
        source if source is not None else make_source(),
        operator, confirmation, existing_entries=entries,
        policy=policy, now=NOW + timedelta(seconds=offset))


def imports_are_safe():
    target = Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_integrity_ledger_v23_7.py")
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
    source1 = make_source(4)
    before1 = source1.to_dict()
    first = record(source1, offset=5)
    source2 = make_source(6)
    second = record(source2, first.entries, offset=7)
    bad_entry = replace(first.entries[0], operator="attacker")
    reverse_entry = replace(
        second.entries[1],
        recorded_at=(NOW + timedelta(seconds=4)).isoformat())

    checks = {
        "Version is V23.7": second.version == "V23.7",
        "Default policy is valid": second.policy_checks_passed,
        "V23.6 integrity source passed": source1.all_checks_passed,
        "Certificate hash passed": second.certificate_hash_checks_passed,
        "Source linkage passed": second.source_linkage_checks_passed,
        "First certificate was recorded":
            first.certificate_recorded and len(first.entries) == 1,
        "Second certificate was recorded":
            second.certificate_recorded and len(second.entries) == 2,
        "Two ledger entries were created": second.total_entry_count == 2,
        "Sequences are chronological":
            [entry.sequence for entry in second.entries] == [1, 2],
        "Ledger hash chain passed":
            not verify_integrity_certificate_ledger(second.entries),
        "Ledger snapshot hash passed":
            second.ledger_snapshot_hash == ledger_snapshot_hash(second.entries),
        "Source remained unchanged": source1.to_dict() == before1,
        "Duplicate certificate was blocked":
            not record(source1, first.entries, offset=8).all_checks_passed,
        "Wrong confirmation was blocked":
            not record(source1, confirmation="WRONG").all_checks_passed,
        "Empty operator was blocked":
            not record(source1, operator="").all_checks_passed,
        "Wrong source type failed":
            not record("bad-source").all_checks_passed,
        "Wrong source version failed":
            not record(replace(source1, version="V23.5")).all_checks_passed,
        "Wrong source status failed":
            not record(replace(
                source1, result_status="BLOCKED")).all_checks_passed,
        "Backward time was blocked":
            not record(source1, offset=3).all_checks_passed,
        "Tampered ledger failed":
            bool(verify_integrity_certificate_ledger((bad_entry,))),
        "Ledger chronology tampering detected":
            bool(verify_integrity_certificate_ledger(
                (second.entries[0], reverse_entry))),
        "Tampered certificate failed":
            not record(replace(
                source1, certificate=replace(
                    source1.certificate,
                    certificate_hash="f" * 64))).all_checks_passed,
        "Broken source linkage was blocked":
            not record(replace(
                source1, source_latest_entry_hash="f" * 64)).all_checks_passed,
        "Invalid policy was blocked":
            not record(source1, policy=replace(
                PortfolioIntegrityLedgerV237Policy(),
                network_access_disabled=False)).all_checks_passed,
        "Forbidden network/broker imports are absent": imports_are_safe(),
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": not second.market_data_api_called,
        "Account API was not called": not second.account_api_called,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized":
            not second.live_execution_authorized,
    }
    with TemporaryDirectory() as directory:
        report, latest = save_ledger_result(second, directory)
        loaded = load_ledger_result(report)
        checks["Result save and load passed"] = (
            report.exists() and latest.exists()
            and loaded["latest_entry_hash"] == second.latest_entry_hash)
    checks["All checks passed"] = all(checks.values())

    print("=" * 80)
    print("AI STOCK BOT V23.7 OFFLINE PAPER PORTFOLIO INTEGRITY LEDGER TEST")
    print("=" * 80)
    print("V23.7 VALIDATION CHECKS")
    print("-" * 80)
    for label, passed in checks.items():
        print(f"{label:<52} : {passed}")
    print("=" * 80)
    if not all(checks.values()):
        failed = [name for name, value in checks.items() if not value]
        raise AssertionError(f"V23.7 failed checks: {failed}")
    print("\nV23.7 offline paper portfolio integrity ledger test completed successfully.")
    print("V23.6 Certificate Hash, Ledger Sequence 및 SHA-256 Hash Chain이 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 없었습니다.")


if __name__ == "__main__":
    main()
