"""Executable checks for V23.9 (standard-library only)."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import timedelta
import io
from pathlib import Path
import tempfile

with redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_ledger_audit_v23_8 import (
        NOW,
        audit as make_audit,
        make_ledger,
    )

from backtest.offline_paper_portfolio_audit_certificate_v23_9 import (
    CONFIRMATION_TEXT,
    DEFAULT_POLICY,
    VERSION,
    PortfolioAuditCertificateV239Policy,
    certify_portfolio_audit_v23_9,
    load_certification_result,
    save_certification_result,
    verify_certificate,
)


def certify(source=None, *, offset=9, operator="paper-auditor", confirmation=CONFIRMATION_TEXT, policy=DEFAULT_POLICY):
    return certify_portfolio_audit_v23_9(
        source if source is not None else make_audit(make_ledger()),
        operator=operator,
        confirmation_text=confirmation,
        now=NOW + timedelta(seconds=offset),
        policy=policy,
    )


source = make_audit(make_ledger())
source_before = source.to_dict()
result = certify(source)
certificate = result.certificate

checks = {
    "Version is V23.9": result.version == VERSION,
    "Default policy is valid": result.policy_check_passed,
    "Policy is immutable": DEFAULT_POLICY.certificate_is_immutable,
    "Invalid policies are blocked": not certify(
        policy=replace(DEFAULT_POLICY, network_access_allowed=True)
    ).all_checks_passed,
    "V23.8 audit source passed": result.source_check_passed,
    "Audit certificate hash passed": result.source_audit_certificate_hash
    == source.audit_certificate.certificate_hash,
    "Source linkage passed": result.linkage_check_passed,
    "Chronology check passed": result.chronology_check_passed,
    "Source remained unchanged": source.to_dict() == source_before,
    "Certificate was created": result.certificate_created,
    "Certificate SHA-256 hash passed": certificate is not None
    and not verify_certificate(certificate),
    "Wrong confirmation was blocked": not certify(confirmation="WRONG").all_checks_passed,
    "Empty operator was blocked": not certify(operator=" ").all_checks_passed,
    "Wrong source type failed": not certify(source={}).all_checks_passed,
    "Wrong source version failed": not certify(
        replace(source, version="V23.7")
    ).all_checks_passed,
    "Wrong source status failed": not certify(
        replace(source, result_status="REJECTED")
    ).all_checks_passed,
    "Backward time was blocked": not certify(offset=1).all_checks_passed,
    "Tampered audit certificate failed": not certify(
        replace(
            source,
            audit_certificate=replace(
                source.audit_certificate, certificate_hash="0" * 64
            ),
        )
    ).all_checks_passed,
    "Broken source linkage was blocked": not certify(
        replace(source, source_latest_entry_hash="f" * 64)
    ).all_checks_passed,
    "Certificate tampering detected": certificate is not None
    and bool(verify_certificate(replace(certificate, operator="tampered"))),
}

with tempfile.TemporaryDirectory() as directory:
    report_path, latest_path = save_certification_result(
        result, Path(directory)
    )
    loaded = load_certification_result(report_path)
    checks["Result save and load passed"] = (
        report_path.exists()
        and latest_path.exists()
        and loaded["version"] == VERSION
        and loaded["certificate"]["certificate_hash"] == certificate.certificate_hash
    )

source_code = Path(
    "backtest/offline_paper_portfolio_audit_certificate_v23_9.py"
).read_text(encoding="utf-8")
imports = {
    node.names[0].name.split(".")[0]
    for node in ast.walk(ast.parse(source_code))
    if isinstance(node, ast.Import)
}
from_imports = {
    (node.module or "").split(".")[0]
    for node in ast.walk(ast.parse(source_code))
    if isinstance(node, ast.ImportFrom)
}
forbidden = {
    "requests", "httpx", "urllib", "socket", "alpaca_trade_api",
    "ib_insync", "ccxt", "boto3",
}
checks.update(
    {
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
        "Execution remains blocked": result.execution_blocked,
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Forbidden network/broker imports are absent": not (
            forbidden & (imports | from_imports)
        ),
    }
)
checks["All checks passed"] = all(checks.values())

print("=" * 80)
print("AI STOCK BOT V23.9 OFFLINE PAPER PORTFOLIO AUDIT CERTIFICATE TEST")
print("=" * 80)
print("V23.9 VALIDATION CHECKS")
print("-" * 80)
for label, passed in checks.items():
    print(f"{label:<55} : {passed}")
print("=" * 80)

if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V23.9 checks failed: {failed}")

print("\nV23.9 offline paper portfolio audit certificate test completed successfully.")
print("V23.8 Audit Certificate Hash, source linkage, chronology, and SHA-256 certificate hash were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
