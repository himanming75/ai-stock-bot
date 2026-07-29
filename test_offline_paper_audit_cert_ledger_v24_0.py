"""Executable V24.0 offline portfolio audit certificate ledger tests."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import io
from pathlib import Path
import tempfile

with redirect_stdout(io.StringIO()):
    from test_offline_paper_portfolio_audit_certificate_v23_9 import NOW, certify

from backtest.offline_paper_audit_cert_ledger_v24_0 import (
    CONFIRMATION_TEXT,
    DEFAULT_POLICY,
    PortfolioAuditCertificateLedgerV240Policy,
    VERSION,
    ledger_snapshot_hash,
    load_ledger_result,
    record_portfolio_audit_certificate_v24_0,
    save_ledger_result,
    validate_policy,
    verify_portfolio_audit_cert_ledger,
)


def blocked(callable_object) -> bool:
    try:
        callable_object()
    except (TypeError, ValueError, PermissionError, FrozenInstanceError):
        return True
    return False


source_one = certify(offset=9)
source_two = certify(offset=11)
source_one_before = deepcopy(source_one)

first = record_portfolio_audit_certificate_v24_0(
    source_one,
    operator="offline-tester",
    confirmation_text=CONFIRMATION_TEXT,
    recorded_at=NOW + timedelta(seconds=10),
)
second = record_portfolio_audit_certificate_v24_0(
    source_two,
    operator="offline-tester",
    confirmation_text=CONFIRMATION_TEXT,
    recorded_at=NOW + timedelta(seconds=12),
    existing_entries=first.entries,
)

checks: dict[str, bool] = {}
checks["Version is V24.0"] = VERSION == "V24.0" and second.version == VERSION
checks["Default policy is valid"] = validate_policy(DEFAULT_POLICY)
checks["Policy is immutable"] = blocked(
    lambda: setattr(DEFAULT_POLICY, "allow_network", True)
)
checks["Invalid policies are blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_one,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
        policy=PortfolioAuditCertificateLedgerV240Policy(allow_network=True),
    )
)
checks["V23.9 source passed"] = source_one.version == "V23.9"
checks["Certificate hash passed"] = (
    first.entries[0].source_certificate_hash
    == source_one.certificate.certificate_hash
)
checks["Source linkage passed"] = (
    first.entries[0].source_certification_result_id
    == source_one.certification_result_id
)
checks["First certificate was recorded"] = first.total_entry_count == 1
checks["Second certificate was recorded"] = second.total_entry_count == 2
checks["Two ledger entries were created"] = len(second.entries) == 2
checks["Sequences are chronological"] = [e.sequence for e in second.entries] == [1, 2]
checks["Ledger SHA-256 hash chain passed"] = verify_portfolio_audit_cert_ledger(
    second.entries
)
checks["Ledger snapshot hash passed"] = (
    second.ledger_snapshot_hash == ledger_snapshot_hash(second.entries)
)
checks["Source remained unchanged"] = source_one == source_one_before
checks["Duplicate certificate was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_one,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
        recorded_at=NOW + timedelta(seconds=13),
        existing_entries=first.entries,
    )
)
checks["Wrong confirmation was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_one, operator="offline-tester", confirmation_text="WRONG"
    )
)
checks["Empty operator was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_one, operator=" ", confirmation_text=CONFIRMATION_TEXT
    )
)
checks["Wrong source type failed"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        {}, operator="offline-tester", confirmation_text=CONFIRMATION_TEXT
    )
)
checks["Backward time was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_two,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
        recorded_at=NOW + timedelta(seconds=9),
        existing_entries=first.entries,
    )
)

tampered_source = deepcopy(source_one)
tampered_source.certificate = replace(
    tampered_source.certificate, certificate_hash="f" * 64
)
checks["Tampered certificate failed"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        tampered_source,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
    )
)

broken_link = deepcopy(source_one)
broken_link.source_audit_result_id = "broken-source"
checks["Broken source linkage was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        broken_link,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
    )
)

tampered_entry = replace(first.entries[0], operator="attacker")
checks["Ledger tampering detected"] = not verify_portfolio_audit_cert_ledger(
    (tampered_entry,)
)
checks["Tampered existing ledger was blocked"] = blocked(
    lambda: record_portfolio_audit_certificate_v24_0(
        source_two,
        operator="offline-tester",
        confirmation_text=CONFIRMATION_TEXT,
        existing_entries=(tampered_entry,),
    )
)

with tempfile.TemporaryDirectory() as temporary_directory:
    result_path = Path(temporary_directory) / "v24_0_result.json"
    save_ledger_result(second, result_path)
    loaded = load_ledger_result(result_path)
    checks["Result save and load passed"] = (
        loaded["version"] == VERSION
        and loaded["ledger_snapshot_hash"] == second.ledger_snapshot_hash
        and len(loaded["entries"]) == 2
    )

source_code = Path(
    "backtest/offline_paper_audit_cert_ledger_v24_0.py"
).read_text(encoding="utf-8")
tree = ast.parse(source_code)
forbidden_roots = {
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "socket",
    "websocket",
    "alpaca",
    "ib_insync",
    "ccxt",
}
imported_roots: set[str] = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported_roots.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imported_roots.add(node.module.split(".")[0])

checks["Forbidden network/broker imports are absent"] = not (
    imported_roots & forbidden_roots
)
checks["Market data API was not called"] = second.market_data_api_called is False
checks["Account API was not called"] = second.account_api_called is False
checks["Network was not accessed"] = second.network_accessed is False
checks["Broker API was not called"] = second.broker_api_called is False
checks["Broker order was not created"] = second.broker_order_created is False
checks["Order was not submitted"] = second.order_submitted is False
checks["Live execution not authorized"] = (
    second.live_execution_authorized is False
)
checks["Execution remains blocked"] = second.execution_blocked is True
checks["Funds were not reserved"] = second.funds_reserved is False
checks["Holdings were not reserved"] = second.holdings_reserved is False
checks["All checks passed"] = all(checks.values())

width = max(len(label) for label in checks)
print("=" * 78)
print("AI STOCK BOT V24.0 OFFLINE PAPER AUDIT CERTIFICATE LEDGER TEST")
print("=" * 78)
for label, passed in checks.items():
    print(f"{label:<{width}} : {passed}")
print("=" * 78)

if not checks["All checks passed"]:
    failed = [label for label, passed in checks.items() if not passed]
    raise AssertionError(f"V24.0 checks failed: {failed}")

print()
print("V24.0 offline paper audit certificate ledger test completed successfully.")
print("V23.9 certificate linkage, ledger sequence, and SHA-256 chain were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
