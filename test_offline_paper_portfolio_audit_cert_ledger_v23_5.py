"""Standalone validation for V23.5 Portfolio Audit Certificate Ledger."""

from __future__ import annotations

import ast
import contextlib
import io
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_portfolio_audit_v23_4 import (
    CONFIRMATION_TEXT as AUDIT_CONFIRMATION,
    audit_portfolio_validation_ledger_v23_4,
)
from backtest.offline_paper_portfolio_audit_cert_ledger_v23_5 import (
    CONFIRMATION_TEXT,
    PortfolioAuditCertLedgerV235Policy,
    ledger_snapshot_hash,
    load_ledger_result,
    record_portfolio_audit_certificate_v23_5,
    save_ledger_result,
    verify_portfolio_audit_cert_ledger,
)
with contextlib.redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_audit_v23_4 import NOW, make_v233_source


def make_audit(offset=0):
    return audit_portfolio_validation_ledger_v23_4(
        make_v233_source(), "paper-auditor", AUDIT_CONFIRMATION,
        now=NOW + timedelta(seconds=offset),
    )


def run(source=None, existing=None, operator="paper-ledger-operator",
        confirmation=CONFIRMATION_TEXT, policy=None, offset=1):
    return record_portfolio_audit_certificate_v23_5(
        source or make_audit(), operator, confirmation,
        existing_entries=existing, policy=policy,
        now=NOW + timedelta(seconds=offset),
    )


def imports_are_safe():
    target = Path(__file__).with_name("backtest").joinpath(
        "offline_paper_portfolio_audit_cert_ledger_v23_5.py")
    tree = ast.parse(target.read_text(encoding="utf-8"))
    forbidden = {"requests", "urllib", "httpx", "socket", "alpaca", "ibapi",
                 "ccxt", "boto3"}
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return not names.intersection(forbidden)


def main():
    source1 = make_audit(0)
    before1 = source1.to_dict()
    first = run(source1, offset=1)
    source2 = make_audit(2)
    before2 = source2.to_dict()
    second = run(source2, first.entries, offset=3)

    tampered_cert = replace(
        source1.certificate, certificate_hash="f" * 64)
    tampered_source = replace(
        source1, certificate=tampered_cert,
        audit_certificate_hash="f" * 64)
    tampered_entry = replace(first.entries[0], operator="attacker")

    checks = {
        "Version is V23.5": second.version == "V23.5",
        "Default policy is valid": first.policy_checks_passed,
        "V23.4 audit source passed": source1.all_checks_passed,
        "First certificate was recorded": first.certificate_recorded,
        "Second certificate was recorded": second.certificate_recorded,
        "Two ledger entries were created": len(second.entries) == 2,
        "Sequences are chronological":
            [x.sequence for x in second.entries] == [1, 2],
        "Ledger hash chain passed":
            not verify_portfolio_audit_cert_ledger(second.entries),
        "Snapshot hash passed":
            second.ledger_snapshot_hash == ledger_snapshot_hash(second.entries),
        "Audit certificate hash was preserved":
            first.entries[0].source_audit_certificate_hash
            == source1.audit_certificate_hash,
        "Source ledger hash was preserved":
            first.entries[0].source_ledger_hash == source1.source_ledger_hash,
        "Sources remained unchanged":
            source1.to_dict() == before1 and source2.to_dict() == before2,
        "Duplicate certificate was blocked":
            not run(source1, first.entries, offset=4).all_checks_passed,
        "Wrong confirmation was blocked":
            not run(source1, confirmation="WRONG").all_checks_passed,
        "Empty operator was blocked":
            not run(source1, operator="").all_checks_passed,
        "Wrong source type failed":
            not run(source="bad-source").all_checks_passed,
        "Wrong source version failed":
            not run(replace(source1, version="V23.3")).all_checks_passed,
        "Wrong source status failed":
            not run(replace(source1, result_status="BLOCKED")).all_checks_passed,
        "Backward time was blocked":
            not run(make_audit(0), offset=-1).all_checks_passed,
        "Tampered audit certificate failed":
            not run(tampered_source).all_checks_passed,
        "Tampered existing ledger was blocked":
            not run(source2, (tampered_entry,), offset=3).all_checks_passed,
        "Invalid policy was blocked":
            not run(source1, policy=replace(
                PortfolioAuditCertLedgerV235Policy(),
                network_access_disabled=False)).all_checks_passed,
        "Forbidden network/broker imports are absent": imports_are_safe(),
        "Source was not modified": not second.source_modified,
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": not second.market_data_api_called,
        "Account API was not called": not second.account_api_called,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
    }
    with TemporaryDirectory() as directory:
        report, latest = save_ledger_result(second, directory)
        loaded = load_ledger_result(report)
        checks["Result save and load passed"] = (
            report.exists() and latest.exists()
            and loaded["ledger_snapshot_hash"] == second.ledger_snapshot_hash
        )
    checks["All checks passed"] = all(checks.values())

    print("=" * 80)
    print("AI STOCK BOT V23.5 OFFLINE PAPER PORTFOLIO AUDIT CERTIFICATE LEDGER TEST")
    print("=" * 80)
    for label, passed in checks.items():
        print(f"{label:<52} : {passed}")
    print("=" * 80)
    if not all(checks.values()):
        failed = [name for name, value in checks.items() if not value]
        raise AssertionError(f"V23.5 failed checks: {failed}")
    print("\nV23.5 offline paper portfolio audit certificate ledger test completed successfully.")
    print("V23.4 Audit Certificate Hash, Ledger Sequence, SHA-256 Hash Chain이 검증되었습니다.")
    print("잔액·보유수량 변경, Network, Broker 주문, 실제 주문 및 Live Execution은 없었습니다.")


if __name__ == "__main__":
    main()
