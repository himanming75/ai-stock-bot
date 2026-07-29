"""Executable checks for V24.1. Run with Python directly."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

with redirect_stdout(StringIO()):
    from test_offline_paper_portfolio_audit_certificate_v23_9 import NOW, certify

from backtest.offline_paper_audit_cert_ledger_v24_0 import (
    CONFIRMATION_TEXT as V240_CONFIRMATION,
    record_portfolio_audit_certificate_v24_0,
)
from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import (
    REQUIRED_CONFIRMATION,
    VERSION,
    AuditCertificateLedgerIntegrityV241Policy,
    audit_certificate_ledger_integrity_v24_1,
    load_audit_result,
    save_audit_result,
    verify_audit_certificate,
)


def check(label: str, condition: bool) -> bool:
    print(f"{label:<50} : {condition}")
    return condition


source_one = certify(offset=9)
source_two = certify(offset=11)
ledger = record_portfolio_audit_certificate_v24_0(
    source_one,
    operator="paper-auditor",
    confirmation_text=V240_CONFIRMATION,
    recorded_at=NOW + timedelta(seconds=10),
)
ledger = record_portfolio_audit_certificate_v24_0(
    source_two,
    operator="paper-auditor",
    confirmation_text=V240_CONFIRMATION,
    recorded_at=NOW + timedelta(seconds=12),
    existing_entries=ledger.entries,
)
ledger_before = deepcopy(ledger)
result = audit_certificate_ledger_integrity_v24_1(
    ledger,
    operator="integrity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat(),
)

checks: list[bool] = []
print("=" * 78)
print("AI STOCK BOT V24.1 OFFLINE PAPER AUDIT CERTIFICATE LEDGER INTEGRITY TEST")
print("=" * 78)
print("V24.1 VALIDATION CHECKS")
print("-" * 78)
checks.append(check("Version is V24.1", result.version == VERSION))
checks.append(check("Default policy is valid", result.policy == AuditCertificateLedgerIntegrityV241Policy()))

try:
    result.policy.source_version = "BROKEN"  # type: ignore[misc]
    immutable = False
except FrozenInstanceError:
    immutable = True
checks.append(check("Policy is immutable", immutable))

invalid_policy_blocked = False
try:
    audit_certificate_ledger_integrity_v24_1(
        ledger,
        operator="integrity-auditor",
        confirmation=REQUIRED_CONFIRMATION,
        created_at=(NOW + timedelta(seconds=14)).isoformat(),
        policy=replace(result.policy, allow_network=True),
    )
except ValueError:
    invalid_policy_blocked = True
checks.append(check("Invalid policies are blocked", invalid_policy_blocked))
checks.append(check("V24.0 ledger source passed", result.source_ledger_verified))
checks.append(check("Ledger hash chain passed", result.hash_chain_verified))
checks.append(check("Source linkage passed", result.certificate is not None and result.certificate.source_ledger_result_id == ledger.ledger_result_id))
checks.append(check("Chronology check passed", result.chronology_verified))
checks.append(check("Entry safety check passed", result.entry_safety_verified))
checks.append(check("Ledger snapshot hash passed", result.snapshot_verified))
checks.append(check("Ledger remained unchanged", ledger == ledger_before))
checks.append(check("Integrity certificate hash passed", result.certificate is not None and not verify_audit_certificate(result.certificate)))
checks.append(check("Five findings passed", len(result.findings) == 5 and all(item.passed for item in result.findings)))

def blocked(callable_) -> bool:
    try:
        callable_()
    except (ValueError, TypeError, PermissionError):
        return True
    return False


checks.append(check("Wrong confirmation was blocked", blocked(lambda: audit_certificate_ledger_integrity_v24_1(
    ledger, operator="integrity-auditor", confirmation="WRONG",
    created_at=(NOW + timedelta(seconds=14)).isoformat()))))
checks.append(check("Empty operator was blocked", blocked(lambda: audit_certificate_ledger_integrity_v24_1(
    ledger, operator=" ", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat()))))
checks.append(check("Wrong source type failed", blocked(lambda: audit_certificate_ledger_integrity_v24_1(
    {}, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat()))))  # type: ignore[arg-type]
checks.append(check("Backward time was blocked", blocked(lambda: audit_certificate_ledger_integrity_v24_1(
    ledger, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW - timedelta(seconds=1)).isoformat()))))

tampered_chain = deepcopy(ledger)
tampered_chain.entries = (
    replace(tampered_chain.entries[0], source_certificate_hash="0" * 64),
    tampered_chain.entries[1],
)
tampered_result = audit_certificate_ledger_integrity_v24_1(
    tampered_chain, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat())
checks.append(check("Tampered ledger failed", not tampered_result.hash_chain_verified and not tampered_result.certificate_created))

broken_snapshot = deepcopy(ledger)
broken_snapshot.ledger_snapshot_hash = "0" * 64
snapshot_result = audit_certificate_ledger_integrity_v24_1(
    broken_snapshot, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat())
checks.append(check("Broken snapshot was detected", not snapshot_result.snapshot_verified))

broken_latest = deepcopy(ledger)
broken_latest.latest_entry_hash = "f" * 64
latest_result = audit_certificate_ledger_integrity_v24_1(
    broken_latest, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat())
checks.append(check("Broken latest hash was detected", not latest_result.snapshot_verified))

unsafe_ledger = deepcopy(ledger)
unsafe_ledger.execution_blocked = False
unsafe_result = audit_certificate_ledger_integrity_v24_1(
    unsafe_ledger, operator="integrity-auditor", confirmation=REQUIRED_CONFIRMATION,
    created_at=(NOW + timedelta(seconds=14)).isoformat())
checks.append(check("Unsafe ledger source failed", not unsafe_result.source_ledger_verified))

assert result.certificate is not None
tampered_certificate = replace(result.certificate, operator="intruder")
checks.append(check("Certificate tampering detected", bool(verify_audit_certificate(tampered_certificate))))

with TemporaryDirectory() as temporary_directory:
    result_path = Path(temporary_directory) / "v24_1_result.json"
    save_audit_result(result, result_path)
    loaded = load_audit_result(result_path)
    save_load_passed = (
        loaded.audit_result_id == result.audit_result_id
        and loaded.certificate == result.certificate
        and loaded.findings == result.findings
    )
checks.append(check("Result save and load passed", save_load_passed))

module_path = Path("backtest/offline_paper_audit_cert_ledger_integrity_v24_1.py")
tree = ast.parse(module_path.read_text(encoding="utf-8"))
forbidden_roots = {
    "requests", "urllib", "http", "httpx", "aiohttp", "socket",
    "alpaca", "ib_insync", "ccxt", "yfinance",
}
imported_roots: set[str] = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported_roots.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported_roots.add(node.module.split(".")[0])
checks.append(check("Forbidden network/broker imports are absent", not (imported_roots & forbidden_roots)))
checks.append(check("Market data API was not called", not result.market_data_api_called))
checks.append(check("Account was not accessed", not result.account_api_called))
checks.append(check("Network was not accessed", not result.network_accessed))
checks.append(check("Broker API was not called", not result.broker_api_called))
checks.append(check("Broker order was not created", not result.broker_order_created))
checks.append(check("Order was not submitted", not result.order_submitted))
checks.append(check("Live execution not authorized", not result.live_execution_authorized))
checks.append(check("Execution remains blocked", result.execution_blocked))
checks.append(check("Funds were not reserved", not result.funds_reserved))
checks.append(check("Holdings were not reserved", not result.holdings_reserved))
all_passed = all(checks)
check("All checks passed", all_passed)
print("=" * 78)

if not all_passed:
    raise AssertionError("V24.1 validation failed")

print()
print("V24.1 offline paper audit certificate ledger integrity audit test completed successfully.")
print("V24.0 Ledger Chain, Snapshot Hash, source immutability, and V24.1 Certificate Hash were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
