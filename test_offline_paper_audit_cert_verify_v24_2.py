"""Executable validation checks for V24.2."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from io import StringIO
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_paper_audit_cert_verify_v24_2 import (
    VERSION,
    REQUIRED_CONFIRMATION,
    AuditCertificateVerificationV242Policy,
    load_verification_result,
    save_verification_result,
    verify_audit_certificate_v24_2,
    verify_verification_certificate,
)


with redirect_stdout(StringIO()):
    from test_offline_paper_audit_cert_ledger_integrity_v24_1 import (
        result as source_result,
    )


VERIFY_TIME = (
    datetime.fromisoformat(source_result.created_at) + timedelta(seconds=1)
).isoformat()


def blocked(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError, PermissionError):
        return True
    return False


result = verify_audit_certificate_v24_2(
    source_result,
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)

checks = {
    "Version is V24.2": result.version == VERSION,
    "Default policy is valid": result.policy
    == AuditCertificateVerificationV242Policy(),
    "Source contract passed": result.source_contract_verified,
    "Certificate hash passed": result.certificate_hash_verified,
    "Findings hash passed": result.findings_hash_verified,
    "Result identity passed": result.result_identity_verified,
    "Source linkage passed": result.linkage_verified,
    "Source safety passed": result.safety_verified,
    "Source remained unchanged": result.source_remained_unchanged,
    "Seven findings were created": len(result.findings) == 7,
    "Verification certificate created": result.certificate_created,
    "Verification completed": result.result_status
    == "AUDIT_CERTIFICATE_VERIFIED",
    "Output certificate hash passed": result.certificate is not None
    and verify_verification_certificate(result.certificate),
    "Wrong confirmation was blocked": blocked(
        lambda: verify_audit_certificate_v24_2(
            source_result,
            operator="offline-auditor",
            confirmation="WRONG",
            verification_time=VERIFY_TIME,
        )
    ),
    "Empty operator was blocked": blocked(
        lambda: verify_audit_certificate_v24_2(
            source_result,
            operator="",
            confirmation=REQUIRED_CONFIRMATION,
            verification_time=VERIFY_TIME,
        )
    ),
    "Wrong source type failed": blocked(
        lambda: verify_audit_certificate_v24_2(
            {},
            operator="offline-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            verification_time=VERIFY_TIME,
        )
    ),
    "Backward time was blocked": blocked(
        lambda: verify_audit_certificate_v24_2(
            source_result,
            operator="offline-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            verification_time="2000-01-01T00:00:00+00:00",
        )
    ),
    "Invalid policy was blocked": blocked(
        lambda: verify_audit_certificate_v24_2(
            source_result,
            operator="offline-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            verification_time=VERIFY_TIME,
            policy=replace(
                AuditCertificateVerificationV242Policy(),
                allow_network=True,
            ),
        )
    ),
}

tampered_certificate_source = replace(
    source_result,
    certificate=replace(source_result.certificate, operator="attacker"),
)
tampered_certificate_result = verify_audit_certificate_v24_2(
    tampered_certificate_source,
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)
checks["Tampered source certificate detected"] = (
    not tampered_certificate_result.certificate_hash_verified
)

tampered_findings_source = replace(
    source_result,
    findings=(
        replace(source_result.findings[0], detail="tampered"),
        *source_result.findings[1:],
    ),
)
tampered_findings_result = verify_audit_certificate_v24_2(
    tampered_findings_source,
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)
checks["Tampered source findings detected"] = (
    not tampered_findings_result.findings_hash_verified
)

tampered_identity_result = verify_audit_certificate_v24_2(
    replace(source_result, audit_result_id="0" * 64),
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)
checks["Tampered result identity detected"] = (
    not tampered_identity_result.result_identity_verified
)

broken_link_source = replace(
    source_result,
    certificate=replace(source_result.certificate, source_ledger_result_id=""),
)
broken_link_result = verify_audit_certificate_v24_2(
    broken_link_source,
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)
checks["Broken source linkage detected"] = not broken_link_result.linkage_verified

unsafe_source_result = verify_audit_certificate_v24_2(
    replace(source_result, execution_blocked=False),
    operator="offline-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    verification_time=VERIFY_TIME,
)
checks["Unsafe source detected"] = not unsafe_source_result.safety_verified

tampered_output = replace(
    result.certificate,
    operator="attacker",
)
checks["Output certificate tampering detected"] = not verify_verification_certificate(
    tampered_output
)

with TemporaryDirectory() as temp_dir:
    saved_path = Path(temp_dir) / "v24_2_result.json"
    save_verification_result(result, saved_path)
    loaded = load_verification_result(saved_path)
    checks["Result save and load passed"] = loaded == result

source_text = Path(
    "backtest/offline_paper_audit_cert_verify_v24_2.py"
).read_text(encoding="utf-8")
tree = ast.parse(source_text)
forbidden_roots = {
    "requests",
    "urllib",
    "http",
    "socket",
    "websocket",
    "aiohttp",
    "alpaca",
    "ib_insync",
    "ccxt",
    "yfinance",
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
checks["Forbidden network/broker imports are absent"] = not (
    imports & forbidden_roots
)

checks.update(
    {
        "Market data API was not called": not result.market_data_api_called,
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
        "Execution remains blocked": result.execution_blocked,
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
    }
)
checks["All checks passed"] = all(checks.values())

print("=" * 78)
print("AI STOCK BOT V24.2 OFFLINE PAPER AUDIT CERTIFICATE VERIFICATION TEST")
print("=" * 78)
for name, passed in checks.items():
    print(f"{name:<48} : {passed}")
print("=" * 78)

if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V24.2 checks failed: {failed}")

print()
print("V24.2 offline paper audit certificate verification test completed successfully.")
print("V24.1 contract, certificate/findings/result hashes, linkage, and safety were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
